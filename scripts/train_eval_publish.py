from __future__ import annotations

import csv
import gc
import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


# --- szl guard -----------------------------------------------------------
def szl_text_tokenizer(obj):
    """A VL processor __call__ is (images, text, videos); unsloth_zoo
    re-dispatches positionally, so a bare string lands in the images slot.
    Resolve the text-modality tokenizer and refuse anything that can still
    reach an image processor."""
    tok = getattr(obj, "tokenizer", obj)
    if hasattr(tok, "image_processor"):
        raise RuntimeError("szl guard: object still exposes image_processor")
    if not callable(tok):
        raise RuntimeError("szl guard: resolved object is not callable")
    return tok

def szl_b64_fix(s):
    if isinstance(s, bytes):
        s = s.decode("ascii", "ignore")
    s = "".join(s.split())
    return s + "=" * (-len(s) % 4)
# -------------------------------------------------------------------------


ROOT = Path.cwd()
PYTHON = Path(sys.executable)
BASE_MODEL = "unsloth/Qwen3.5-0.8B"
HF_REPO = os.environ.get(
    "HF_STUDY_REPO",
    "SZLHOLDINGS/szl-triage-qwen3.5-0.8b-lora-study5",
)

RUN1_COMMIT = "427a70eb0804d814bf32d2cfc2713e230e468691"
RUN1_TAG = "triage-lora-run1"
STUDY_TAG = "triage-lora-study5-measured-20260922-111314"

SEEDS = [11, 23, 37, 53, 71]
NEW_SEEDS = [23, 37, 53, 71]

TRAINER = ROOT / "scripts" / "train_lora.py"
STUDY = ROOT / "out" / "train" / "study"
CONTROL = STUDY / "control"
FROZEN = STUDY / "frozen"
EVALUATION = STUDY / "evaluation"
EVIDENCE = ROOT / "evidence" / "five-seed-study"
PUBLISH = ROOT / "out" / "publish" / "triage-lora-study5"

RUN1_ADAPTER = ROOT / "out" / "train" / "adapter"
RUN1_RECEIPT = ROOT / "out" / "train" / "training_receipt.json"

for directory in (STUDY, CONTROL, FROZEN, EVALUATION):
    directory.mkdir(parents=True, exist_ok=True)


def assert_text_only_tokenizer(tok):
    """Preflight guard: refuse a VL Processor being called positionally as a tokenizer.

    Qwen3VLProcessor.__call__ has signature (images, text, videos, ...), so a bare
    positional call routes the rendered chat string into `images`, which then fails
    inside load_image() as "Incorrect image source" / "Incorrect padding".
    """
    import inspect
    if getattr(tok, "tokenizer", None) is None:
        return "plain-tokenizer"
    params = list(inspect.signature(type(tok).__call__).parameters)
    if len(params) > 1 and params[1] == "images":
        raise RuntimeError(
            f"{type(tok).__name__} takes `images` as its first positional parameter. "
            "Call with text= keyword, or use tok.tokenizer for text-only evaluation."
        )
    return "processor-ok"


def text_only_encode(tok, rendered, return_tensors="pt"):
    """Text-only encode helper that never sends text through a VL image slot."""
    inner = getattr(tok, "tokenizer", None)
    if inner is not None:
        if hasattr(inner, "image_processor"):
            raise RuntimeError("szl guard: inner tokenizer still exposes image_processor")
        return inner(
            rendered,
            return_tensors=return_tensors,
            add_special_tokens=False,
        )

    if hasattr(tok, "image_processor"):
        return tok(
            text=rendered,
            return_tensors=return_tensors,
            add_special_tokens=False,
        )

    return tok(
        rendered,
        return_tensors=return_tensors,
        add_special_tokens=False,
    )


def build_generation_inputs(tokenizer, prompt: str, device):
    """Build model-ready text-only inputs through the model-native chat template.

    Do not render a string and send it back through a VL processor positionally:
    for Qwen VL processors the positional argument can be interpreted as images.
    Using tokenize=True and return_dict=True lets the processor/tokenizer produce
    input_ids directly under the model's own chat-template semantics.
    """
    messages = [{"role": "user", "content": prompt}]

    template_kwargs = dict(
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt",
    )

    try:
        inputs = tokenizer.apply_chat_template(
            messages,
            enable_thinking=False,
            **template_kwargs,
        )
    except TypeError:
        inputs = tokenizer.apply_chat_template(messages, **template_kwargs)

    if hasattr(inputs, "to"):
        return inputs.to(device)

    return {
        key: value.to(device) if hasattr(value, "to") else value
        for key, value in inputs.items()
    }

def log(message: str) -> None:
    print(message, flush=True)


def canonical(value) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def run(
    command: list[str],
    *,
    cwd: Path = ROOT,
    log_path: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess:
    printable = " ".join(str(item) for item in command)
    log(f"\n$ {printable}")

    handle = None

    try:
        if log_path is not None:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            handle = log_path.open("a", encoding="utf-8", newline="\n")

        process = subprocess.Popen(
            [str(item) for item in command],
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

        captured = []

        assert process.stdout is not None

        for line in process.stdout:
            print(line, end="", flush=True)
            captured.append(line)

            if handle is not None:
                handle.write(line)
                handle.flush()

        code = process.wait()
        stdout = "".join(captured)

        result = subprocess.CompletedProcess(
            command,
            code,
            stdout=stdout,
            stderr=None,
        )

        if check and code != 0:
            raise RuntimeError(
                f"Command failed with exit code {code}: {printable}"
            )

        return result

    finally:
        if handle is not None:
            handle.close()


def command_output(command: list[str]) -> str:
    result = subprocess.run(
        [str(item) for item in command],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return result.stdout.strip()


def preflight() -> dict:
    log("\n=== PREFLIGHT ===")

    try:
        import torch
        import unsloth
        import huggingface_hub
    except Exception as exc:
        raise RuntimeError(
            f"ML stack import failed: {type(exc).__name__}: {exc}"
        ) from exc

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable")

    capability = torch.cuda.get_device_capability()
    required_arch = f"sm_{capability[0]}{capability[1]}"
    available_arches = torch.cuda.get_arch_list()

    if required_arch not in available_arches:
        raise RuntimeError(
            f"GPU requires {required_arch}; wheel contains {available_arches}"
        )

    required = [
        TRAINER,
        RUN1_ADAPTER / "adapter_model.safetensors",
        RUN1_ADAPTER / "adapter_config.json",
        RUN1_RECEIPT,
    ]

    for path in required:
        if not path.exists():
            raise RuntimeError(f"Required path is missing: {path}")

    tag_commit = command_output(
        ["git", "rev-list", "-n", "1", RUN1_TAG]
    )

    if tag_commit != RUN1_COMMIT:
        raise RuntimeError(
            f"{RUN1_TAG} resolves to {tag_commit}; expected {RUN1_COMMIT}"
        )

    token = os.environ.get("HF_TOKEN", "").strip()

    if not token:
        token = None

    from huggingface_hub import HfApi

    api = HfApi(token=token)
    identity = api.whoami(token=token or None)

    receipt = {
        "schema": "szl.study-preflight/v1",
        "python": sys.version,
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "device": torch.cuda.get_device_name(0),
        "capability": list(capability),
        "required_arch": required_arch,
        "available_arches": available_arches,
        "unsloth": getattr(unsloth, "__version__", "unknown"),
        "huggingface_hub": getattr(
            huggingface_hub,
            "__version__",
            "unknown",
        ),
        "hugging_face_identity": identity.get(
            "name",
            identity.get("fullname", "authenticated"),
        ),
        "hub_repository": HF_REPO,
        "run1_tag": RUN1_TAG,
        "run1_commit": RUN1_COMMIT,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }

    write_json(STUDY / "preflight.json", receipt)
    log(json.dumps(receipt, indent=2))

    return receipt


def text_of(row: dict) -> str:
    for key in ("input", "text", "prompt"):
        value = row.get(key)

        if isinstance(value, str):
            return value

    return json.dumps(row, ensure_ascii=False)


def family_key(text: str) -> str:
    normalized = re.sub(r"[^a-z ]", " ", text.lower())
    prefix = " ".join(normalized.split()[:8])
    return hashlib.sha1(prefix.encode()).hexdigest()[:10]


def row_id(row: dict) -> str:
    return hashlib.sha256(canonical(row).encode()).hexdigest()


def choose_corpus() -> Path:
    candidates = [
        ROOT / "output" / "triage_distill_v0.5.0.jsonl",
        ROOT / "output" / "triage_distill.jsonl",
    ]

    for path in candidates:
        if path.exists():
            return path

    raise RuntimeError("No supported distillation corpus was found")


def freeze_split() -> tuple[Path, list[dict]]:
    log("\n=== FREEZE TEMPLATE-FAMILY SPLIT ===")

    corpus = choose_corpus()

    rows = [
        json.loads(line)
        for line in corpus.read_text(
            encoding="utf-8-sig"
        ).splitlines()
        if line.strip()
    ]

    families: dict[str, list[dict]] = {}

    for row in rows:
        families.setdefault(
            family_key(text_of(row)),
            [],
        ).append(row)

    keys = sorted(families)
    cut = int(len(keys) * 0.8)

    train_families = keys[:cut]
    held_families = keys[cut:]

    train_rows = [
        row
        for key in train_families
        for row in families[key]
    ]

    held_rows = [
        row
        for key in held_families
        for row in families[key]
    ]

    if len(rows) != 628:
        raise RuntimeError(
            f"Expected 628 corpus rows; found {len(rows)}"
        )

    if len(train_rows) != 515 or len(held_rows) != 113:
        raise RuntimeError(
            "Expected frozen 515/113 split; found "
            f"{len(train_rows)}/{len(held_rows)}"
        )

    if set(train_families) & set(held_families):
        raise RuntimeError("Template-family overlap detected")

    train_path = FROZEN / "train.jsonl"
    held_path = FROZEN / "held.jsonl"

    train_records = [
        {
            "row_id": row_id(row),
            "family": family_key(text_of(row)),
            "row": row,
        }
        for row in train_rows
    ]

    held_records = [
        {
            "row_id": row_id(row),
            "family": family_key(text_of(row)),
            "prompt": text_of(row),
            "target": {
                "label": row.get("label"),
                "state": row.get("state"),
                "evidence": row.get("evidence", []),
            },
        }
        for row in held_rows
    ]

    train_path.write_text(
        "\n".join(canonical(item) for item in train_records) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    held_path.write_text(
        "\n".join(canonical(item) for item in held_records) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    manifest = {
        "schema": "szl.frozen-family-split/v1",
        "base_model": BASE_MODEL,
        "run1_commit": RUN1_COMMIT,
        "run1_tag": RUN1_TAG,
        "corpus": str(corpus.relative_to(ROOT)).replace("\\", "/"),
        "corpus_sha256": sha256_file(corpus),
        "rows": len(rows),
        "families": len(keys),
        "train_rows": len(train_rows),
        "held_rows": len(held_rows),
        "train_families": len(train_families),
        "held_families": len(held_families),
        "train_manifest_sha256": sha256_file(train_path),
        "held_manifest_sha256": sha256_file(held_path),
        "split_method": (
            "Sorted template-family hash; first 80 percent train; "
            "remaining families held out"
        ),
        "seeds": SEEDS,
        "release_gate": "11/12",
        "release_status": "BLOCKED",
        "promotion_status": "NOT_PROMOTABLE",
        "publication_status": "PUBLIC_EXPERIMENTAL_ARTIFACT",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }

    write_json(FROZEN / "experiment_manifest.json", manifest)
    log(json.dumps(manifest, indent=2))

    return corpus, held_records


def validate_training_receipt(
    receipt_path: Path,
    adapter_path: Path,
    seed: int,
) -> dict:
    if not receipt_path.exists():
        raise RuntimeError(
            f"Training receipt missing for seed {seed}: {receipt_path}"
        )

    if not (adapter_path / "adapter_model.safetensors").exists():
        raise RuntimeError(
            f"Adapter weights missing for seed {seed}: {adapter_path}"
        )

    if not (adapter_path / "adapter_config.json").exists():
        raise RuntimeError(
            f"Adapter configuration missing for seed {seed}"
        )

    receipt = json.loads(
        receipt_path.read_text(encoding="utf-8-sig")
    )

    if receipt.get("state") != "MEASURED":
        raise RuntimeError(
            f"Seed {seed} state is not MEASURED"
        )

    if receipt.get("binding_check") != "PASS":
        raise RuntimeError(
            f"Seed {seed} binding check is not PASS"
        )

    recorded_seed = (
        receipt.get("hyperparameters", {}).get("seed")
    )

    if int(recorded_seed) != seed:
        raise RuntimeError(
            f"Seed receipt mismatch: expected {seed}, "
            f"found {recorded_seed}"
        )

    return receipt


def train_new_seeds() -> dict[int, dict]:
    log("\n=== TRAIN FOUR ADDITIONAL SEEDS ===")

    source = TRAINER.read_text(encoding="utf-8")

    required_markers = [
        'OUT = Path("out/train"); OUT.mkdir(parents=True, exist_ok=True)',
        "random_state=11",
        "seed=11",
        '"seed": 11',
    ]

    for marker in required_markers:
        if marker not in source:
            raise RuntimeError(
                f"Tagged trainer marker changed or missing: {marker}"
            )

    receipts: dict[int, dict] = {}

    run1_receipt = validate_training_receipt(
        RUN1_RECEIPT,
        RUN1_ADAPTER,
        11,
    )
    receipts[11] = run1_receipt

    for seed in NEW_SEEDS:
        name = f"seed-{seed:03d}"
        relative_output = f"out/train/study/{name}"
        output_dir = ROOT / relative_output
        adapter_path = output_dir / "adapter"
        receipt_path = output_dir / "training_receipt.json"
        training_log = output_dir / "training.log"

        if receipt_path.exists():
            receipts[seed] = validate_training_receipt(
                receipt_path,
                adapter_path,
                seed,
            )
            log(f"{name}: measured adapter already exists; preserving it")
            continue

        if output_dir.exists() and any(output_dir.iterdir()):
            raise RuntimeError(
                f"{name} contains an incomplete run. "
                "Inspect it instead of silently overwriting it."
            )

        output_dir.mkdir(parents=True, exist_ok=True)

        patched = source.replace(
            'OUT = Path("out/train"); OUT.mkdir(parents=True, exist_ok=True)',
            (
                f'OUT = Path("{relative_output}"); '
                "OUT.mkdir(parents=True, exist_ok=True)"
            ),
        )

        patched = patched.replace(
            "random_state=11",
            f"random_state={seed}",
        )

        patched = patched.replace(
            "seed=11",
            f"seed={seed}",
        )

        patched = patched.replace(
            '"seed": 11',
            f'"seed": {seed}',
        )

        patched_trainer = CONTROL / f"train_{name}.py"
        patched_trainer.write_text(
            patched,
            encoding="utf-8",
            newline="\n",
        )

        log(f"\n=== TRAIN {name} ===")

        run(
            [str(PYTHON), str(patched_trainer)],
            cwd=ROOT,
            log_path=training_log,
        )

        receipts[seed] = validate_training_receipt(
            receipt_path,
            adapter_path,
            seed,
        )

    return receipts


def adapter_path_for_seed(seed: int) -> Path:
    if seed == 11:
        return RUN1_ADAPTER

    return STUDY / f"seed-{seed:03d}" / "adapter"


def strict_json(raw: str) -> dict | None:
    try:
        value = json.loads(raw.strip())
    except Exception:
        return None

    if not isinstance(value, dict):
        return None

    required = {"label", "state", "evidence"}

    if not required.issubset(value):
        return None

    if not isinstance(value.get("evidence"), list):
        return None

    return value


def load_model(model_name: str):
    import torch
    from unsloth import FastLanguageModel

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=1024,
        load_in_4bit=False,
        dtype=torch.bfloat16,
    )

    FastLanguageModel.for_inference(model)
    model.eval()

    return model, tokenizer


def render_prompt(tokenizer, prompt: str) -> str:
    messages = [{"role": "user", "content": prompt}]

    try:
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
    except TypeError:
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )


def generate(model, tokenizer, prompt: str) -> tuple[str, float]:
    import torch

    device = next(model.parameters()).device
    inputs = build_generation_inputs(tokenizer, prompt, device)

    started = time.perf_counter()

    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=192,
            do_sample=False,
            use_cache=True,
            pad_token_id=getattr(getattr(tokenizer, "tokenizer", tokenizer), "eos_token_id", None),
        )

    latency = time.perf_counter() - started
    prompt_len = inputs["input_ids"].shape[-1]
    text_tok = getattr(tokenizer, "tokenizer", tokenizer)
    raw = text_tok.decode(output[0][prompt_len:], skip_special_tokens=True)
    return raw, latency
def safe_ratio(numerator: int, denominator: int):
    if denominator == 0:
        return None

    return numerator / denominator


def evaluate_target(
    name: str,
    model_name: str,
    held_records: list[dict],
) -> dict:
    metrics_path = EVALUATION / f"metrics-{name}.json"
    predictions_path = EVALUATION / f"predictions-{name}.jsonl"

    if metrics_path.exists() and predictions_path.exists():
        existing = json.loads(
            metrics_path.read_text(encoding="utf-8-sig")
        )

        if (
            existing.get("held_rows") == 113
            and existing.get("held_manifest_sha256")
            == sha256_file(FROZEN / "held.jsonl")
        ):
            log(f"{name}: existing evaluation is complete; preserving it")
            return existing

    log(f"\n=== EVALUATE {name} ===")

    model, tokenizer = load_model(model_name)

    counts = {
        "held_rows": 0,
        "strict_json": 0,
        "label_exact": 0,
        "state_exact": 0,
        "joint_exact": 0,
        "target_evidence_exact": 0,
        "predicted_evidence_spans": 0,
        "grounded_evidence_spans": 0,
        "refusal_rows": 0,
        "refusal_fidelity": 0,
        "false_label_on_refusal": 0,
    }

    predictions = []

    for index, record in enumerate(held_records, start=1):
        raw, latency = generate(
            model,
            tokenizer,
            record["prompt"],
        )

        parsed = strict_json(raw)
        target = record["target"]

        if parsed is None:
            predicted_label = None
            predicted_state = None
            predicted_evidence = []
        else:
            counts["strict_json"] += 1
            predicted_label = parsed.get("label")
            predicted_state = parsed.get("state")
            predicted_evidence = parsed.get("evidence", [])

        label_exact = predicted_label == target.get("label")
        state_exact = predicted_state == target.get("state")
        joint_exact = label_exact and state_exact

        target_evidence_exact = (
            predicted_evidence == target.get("evidence", [])
        )

        grounded_flags = [
            isinstance(span, str)
            and span in record["prompt"]
            for span in predicted_evidence
        ]

        counts["held_rows"] += 1
        counts["label_exact"] += int(label_exact)
        counts["state_exact"] += int(state_exact)
        counts["joint_exact"] += int(joint_exact)
        counts["target_evidence_exact"] += int(
            target_evidence_exact
        )

        counts["predicted_evidence_spans"] += len(
            grounded_flags
        )
        counts["grounded_evidence_spans"] += sum(
            grounded_flags
        )

        if target.get("state") == "REVIEW":
            counts["refusal_rows"] += 1

            if predicted_state == "REVIEW":
                counts["refusal_fidelity"] += 1
            else:
                counts["false_label_on_refusal"] += 1

        predictions.append(
            {
                "row_id": record["row_id"],
                "family": record["family"],
                "target": target,
                "raw_output": raw,
                "parsed": parsed,
                "label_exact": label_exact,
                "state_exact": state_exact,
                "joint_exact": joint_exact,
                "target_evidence_exact": target_evidence_exact,
                "grounded_evidence_flags": grounded_flags,
                "latency_seconds": latency,
            }
        )

        log(f"{name}: {index}/113")

    predictions_path.write_text(
        "\n".join(canonical(item) for item in predictions) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    failures = [
        item
        for item in predictions
        if (
            item["parsed"] is None
            or not item["joint_exact"]
            or not all(item["grounded_evidence_flags"])
        )
    ]

    failures_path = EVALUATION / f"failures-{name}.jsonl"

    failures_path.write_text(
        (
            "\n".join(canonical(item) for item in failures) + "\n"
            if failures
            else ""
        ),
        encoding="utf-8",
        newline="\n",
    )

    latencies = [
        item["latency_seconds"]
        for item in predictions
    ]

    metrics = {
        "schema": "szl.frozen-held-evaluation/v1",
        "name": name,
        "base_model": BASE_MODEL,
        "model_source": model_name,
        "held_rows": counts["held_rows"],
        "held_manifest_sha256": sha256_file(
            FROZEN / "held.jsonl"
        ),
        "decoding": {
            "do_sample": False,
            "max_new_tokens": 192,
            "malformed_json_repair": False,
        },
        **counts,
        "strict_json_rate": safe_ratio(
            counts["strict_json"],
            counts["held_rows"],
        ),
        "label_accuracy": safe_ratio(
            counts["label_exact"],
            counts["held_rows"],
        ),
        "state_accuracy": safe_ratio(
            counts["state_exact"],
            counts["held_rows"],
        ),
        "joint_accuracy": safe_ratio(
            counts["joint_exact"],
            counts["held_rows"],
        ),
        "target_evidence_exact_rate": safe_ratio(
            counts["target_evidence_exact"],
            counts["held_rows"],
        ),
        "evidence_grounding_rate": safe_ratio(
            counts["grounded_evidence_spans"],
            counts["predicted_evidence_spans"],
        ),
        "refusal_fidelity_rate": safe_ratio(
            counts["refusal_fidelity"],
            counts["refusal_rows"],
        ),
        "median_latency_seconds": statistics.median(
            latencies
        ),
        "failure_rows": len(failures),
        "predictions_sha256": sha256_file(
            predictions_path
        ),
        "failures_sha256": sha256_file(
            failures_path
        ),
        "release_gate": "11/12",
        "release_status": "BLOCKED",
        "promotion_status": "NOT_PROMOTABLE",
        "publication_status": "PUBLIC_EXPERIMENTAL_ARTIFACT",
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    write_json(metrics_path, metrics)
    log(json.dumps(metrics, indent=2))

    del model
    del tokenizer

    gc.collect()

    import torch
    torch.cuda.empty_cache()

    return metrics


def run_all_evaluations(held_records: list[dict]) -> list[dict]:
    results = []

    results.append(
        evaluate_target(
            "base",
            BASE_MODEL,
            held_records,
        )
    )

    for seed in SEEDS:
        name = f"seed-{seed:03d}"

        results.append(
            evaluate_target(
                name,
                str(adapter_path_for_seed(seed)),
                held_records,
            )
        )

    return results


def aggregate_results(metrics: list[dict]) -> dict:
    log("\n=== AGGREGATE RESULTS ===")

    adapters = [
        metric
        for metric in metrics
        if metric["name"].startswith("seed-")
    ]

    scalar_fields = [
        "strict_json_rate",
        "label_accuracy",
        "state_accuracy",
        "joint_accuracy",
        "target_evidence_exact_rate",
        "evidence_grounding_rate",
        "refusal_fidelity_rate",
        "median_latency_seconds",
    ]

    summary = {}

    for field in scalar_fields:
        values = [
            metric[field]
            for metric in adapters
            if metric.get(field) is not None
        ]

        summary[field] = {
            "n": len(values),
            "mean": statistics.fmean(values)
            if values else None,
            "sample_std": statistics.stdev(values)
            if len(values) > 1 else None,
            "min": min(values) if values else None,
            "max": max(values) if values else None,
        }

    aggregate = {
        "schema": "szl.five-seed-aggregate/v1",
        "base_model": BASE_MODEL,
        "seeds": SEEDS,
        "held_rows": 113,
        "targets": metrics,
        "five_seed_summary": summary,
        "release_gate": "11/12",
        "release_status": "BLOCKED",
        "promotion_status": "NOT_PROMOTABLE",
        "publication_status": "PUBLIC_EXPERIMENTAL_ARTIFACT",
        "interpretation": (
            "Training and frozen evaluation are measured. "
            "Public publication is authorized. Promotion is not "
            "asserted because the existing contamination and release "
            "gates remain attached to the evidence."
        ),
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    write_json(
        EVALUATION / "aggregate_metrics.json",
        aggregate,
    )

    csv_path = EVALUATION / "metrics.csv"

    fields = [
        "name",
        "strict_json_rate",
        "label_accuracy",
        "state_accuracy",
        "joint_accuracy",
        "target_evidence_exact_rate",
        "evidence_grounding_rate",
        "refusal_fidelity_rate",
        "false_label_on_refusal",
        "failure_rows",
        "median_latency_seconds",
    ]

    with csv_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
        )

        writer.writeheader()

        for metric in metrics:
            writer.writerow(
                {
                    field: metric.get(field)
                    for field in fields
                }
            )

    log(json.dumps(aggregate, indent=2))
    return aggregate


def collect_evidence(
    training_receipts: dict[int, dict],
    aggregate: dict,
) -> list[dict]:
    log("\n=== BUILD EVIDENCE PACKAGE ===")

    if EVIDENCE.exists():
        shutil.rmtree(EVIDENCE)

    (EVIDENCE / "frozen").mkdir(
        parents=True,
        exist_ok=True,
    )
    (EVIDENCE / "evaluation").mkdir(
        parents=True,
        exist_ok=True,
    )
    (EVIDENCE / "training").mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copytree(
        FROZEN,
        EVIDENCE / "frozen",
        dirs_exist_ok=True,
    )

    shutil.copytree(
        EVALUATION,
        EVIDENCE / "evaluation",
        dirs_exist_ok=True,
    )

    adapter_index = []

    for seed in SEEDS:
        name = f"seed-{seed:03d}"
        adapter = adapter_path_for_seed(seed)

        if seed == 11:
            receipt_source = RUN1_RECEIPT
        else:
            receipt_source = (
                STUDY
                / name
                / "training_receipt.json"
            )

        receipt_target = (
            EVIDENCE
            / "training"
            / f"training_receipt-{name}.json"
        )

        shutil.copy2(
            receipt_source,
            receipt_target,
        )

        adapter_hash = sha256_file(
            adapter / "adapter_model.safetensors"
        )

        receipt = training_receipts[seed]

        adapter_index.append(
            {
                "seed": seed,
                "local_path": str(
                    adapter.relative_to(ROOT)
                ).replace("\\", "/"),
                "adapter_sha256": adapter_hash,
                "final_training_loss": receipt.get(
                    "final_training_loss"
                ),
                "seconds": receipt.get("seconds"),
                "binding_check": receipt.get(
                    "binding_check"
                ),
                "release_status": "BLOCKED",
                "promotion_status": receipt.get(
                    "promotion_status",
                    "NOT_PROMOTABLE",
                ),
                "publication_status": (
                    "PUBLIC_EXPERIMENTAL_ARTIFACT"
                ),
            }
        )

    write_json(
        EVIDENCE / "adapter-index.json",
        adapter_index,
    )

    try:
        nvidia_smi = command_output(["nvidia-smi"])
    except Exception as exc:
        nvidia_smi = f"unavailable: {exc}"

    try:
        pip_freeze = command_output(
            [str(PYTHON), "-m", "pip", "freeze"]
        ).splitlines()
    except Exception as exc:
        pip_freeze = [f"unavailable: {exc}"]

    environment = {
        "schema": "szl.five-seed-environment/v1",
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "repository_commit_before_study_commit": (
            command_output(["git", "rev-parse", "HEAD"])
        ),
        "branch": command_output(
            ["git", "branch", "--show-current"]
        ),
        "python": sys.version,
        "pip_freeze": pip_freeze,
        "nvidia_smi": nvidia_smi,
        "hub_repository": HF_REPO,
        "release_gate": "11/12",
        "release_status": "BLOCKED",
        "promotion_status": "NOT_PROMOTABLE",
        "publication_status": "PUBLIC_EXPERIMENTAL_ARTIFACT",
    }

    write_json(
        EVIDENCE / "environment-receipt.json",
        environment,
    )

    evidence_readme = """# TypeSafe Triage five-seed study

This directory contains the measured evidence for seeds 11, 23, 37, 53,
and 71.

The same 113-row template-family holdout was used for the untouched base
model and every adapter. Decoding was greedy. Malformed JSON was not
silently repaired.

Public publication is authorized. Training and evaluation are measured.
Release remains BLOCKED at 11/12, and promotion is not asserted while the
recorded contamination verdict remains unresolved.

The model artifacts are published at:

https://huggingface.co/{repo}
""".format(repo=HF_REPO)

    (EVIDENCE / "README.md").write_text(
        evidence_readme,
        encoding="utf-8",
        newline="\n",
    )

    return adapter_index


def percentage(value) -> str:
    if value is None:
        return "N/A"

    return f"{value * 100:.1f}%"


def build_model_card(
    metrics: list[dict],
    aggregate: dict,
    adapter_index: list[dict],
) -> str:
    metric_by_name = {
        metric["name"]: metric
        for metric in metrics
    }

    rows = []

    for name in [
        "base",
        "seed-011",
        "seed-023",
        "seed-037",
        "seed-053",
        "seed-071",
    ]:
        metric = metric_by_name[name]

        rows.append(
            "| {name} | {json_rate} | {label} | {state} | "
            "{joint} | {refusal} | {grounding} | {failures} |".format(
                name=name,
                json_rate=percentage(
                    metric.get("strict_json_rate")
                ),
                label=percentage(
                    metric.get("label_accuracy")
                ),
                state=percentage(
                    metric.get("state_accuracy")
                ),
                joint=percentage(
                    metric.get("joint_accuracy")
                ),
                refusal=percentage(
                    metric.get("refusal_fidelity_rate")
                ),
                grounding=percentage(
                    metric.get("evidence_grounding_rate")
                ),
                failures=metric.get("failure_rows"),
            )
        )

    metric_table = "\n".join(rows)

    joint_summary = aggregate[
        "five_seed_summary"
    ]["joint_accuracy"]

    card = f"""---
base_model: {BASE_MODEL}
library_name: peft
pipeline_tag: text-generation
tags:
- peft
- lora
- unsloth
- qwen3.5
- structured-output
- triage
- reproducible-evaluation
- experimental
---

# SZL TypeSafe Triage · Five-Seed LoRA Study

> **A measured model artifact with its limits attached.**

This repository contains five LoRA training runs for structured triage:
seeds **11, 23, 37, 53, and 71**. It includes the default adapter at the
repository root, every seed under `adapters/`, frozen evaluation identity,
raw predictions, failure records, training receipts, and aggregate metrics.

## Status

| Boundary | Status |
|---|---|
| Public model publication | **Published** |
| Training | **Measured** |
| Frozen held-family evaluation | **Measured** |
| Release gate | **BLOCKED — 11/12** |
| Promotion | **NOT_PROMOTABLE** |
| Production replacement | **No** |

**Published does not mean promoted.** The owner authorized publication of
the trained research artifact. The existing contamination verdict and
release boundary remain visible instead of being removed.

## What it does

The adapter accepts a triage input and is trained to return only:

```json
{{"label":"...","state":"...","evidence":["..."]}}
```

In plain language:

- `label` is the model's proposed category.
- `state` records whether it can decide or needs review.
- `evidence` contains text spans intended to come directly from the input.
- A `REVIEW` state is a refusal to overclaim.

## Study design

- Base model: `{BASE_MODEL}`
- LoRA rank: 16
- LoRA alpha: 16
- Epochs: 3
- Learning rate: 0.0002
- Precision: bfloat16
- Quantization during training: none
- Effective batch size: 4
- Training rows: 515
- Held-family rows: 113
- Seeds: 11, 23, 37, 53, 71
- Split rule: template families are kept together
- Evaluation decoding: greedy
- Malformed JSON repair: disabled

## Measured results

| Target | Valid JSON | Label | State | Joint | Refusal fidelity | Evidence grounded | Failure rows |
|---|---:|---:|---:|---:|---:|---:|---:|
{metric_table}

Across the five adapters, mean joint accuracy was
**{percentage(joint_summary.get("mean"))}**, with sample standard deviation
**{percentage(joint_summary.get("sample_std")) if joint_summary.get("sample_std") is not None else "N/A"}**.

These results describe this frozen 113-row family holdout. They do not
establish broad generalization, calibration, or production readiness.

## Repository layout

```text
README.md
adapter_config.json
adapter_model.safetensors
tokenizer files
adapters/
  seed-011/
  seed-023/
  seed-037/
  seed-053/
  seed-071/
evidence/
  frozen/
  training/
  evaluation/
  adapter-index.json
  environment-receipt.json
```

The root adapter is seed 11, retained as the tagged first measured run.
The additional seed directories support reproducibility and stability
inspection.

## Quick start

```python
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

repo = "{HF_REPO}"
base = "{BASE_MODEL}"

tokenizer = AutoTokenizer.from_pretrained(repo)

model = AutoModelForCausalLM.from_pretrained(
    base,
    torch_dtype=torch.bfloat16,
    device_map="auto",
)

model = PeftModel.from_pretrained(model, repo)
model.eval()

messages = [
    {{
        "role": "user",
        "content": "Your triage input goes here."
    }}
]

prompt = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True,
)

inputs = build_generation_inputs(tokenizer, "Your triage input goes here.", model.device)

with torch.no_grad():
    output = model.generate(
        **inputs,
        max_new_tokens=192,
        do_sample=False,
        pad_token_id=getattr(tokenizer, "tokenizer", tokenizer).eos_token_id,
    )

reply = tokenizer.decode(
    output[inputs["input_ids"].shape:],[3]
    skip_special_tokens=True,
)

print(reply)
```

## Using another seed

Download the repository and load one of these local directories:

```text
adapters/seed-023
adapters/seed-037
adapters/seed-053
adapters/seed-071
```

Each directory is a complete PEFT adapter. The SHA-256 digest for every
adapter is recorded in `evidence/adapter-index.json`.

## Evaluation rules

The held set was separated by template family rather than random row.
This reduces direct template leakage between training and evaluation.

Every target was scored for:

- Strict JSON validity
- Exact label agreement
- Exact state agreement
- Joint label-and-state agreement
- Refusal fidelity
- False labels on refusal cases
- Evidence grounding
- Exact target-evidence agreement

Raw predictions and complete failure records are included so the headline
numbers can be audited.

## Limitations

- Release remains blocked at 11/12.
- Promotion has not been established.
- The recorded contamination verdict still travels with the artifact.
- The model is not calibrated.
- The study does not establish generalization outside the frozen holdout.
- The model is not a replacement for the deterministic decision engine.
- Generated output must be parsed and validated before downstream use.
- High-impact decisions require human or deterministic review.

## Reproducibility

Source repository:

https://github.com/szl-holdings/szl-typesafe-triage

First measured run:

https://github.com/szl-holdings/szl-typesafe-triage/releases/tag/{RUN1_TAG}

Five-seed evidence tag:

https://github.com/szl-holdings/szl-typesafe-triage/releases/tag/{STUDY_TAG}

## Citation

If this artifact is discussed, describe it as:

> SZL TypeSafe Triage five-seed LoRA study: training and frozen evaluation
> measured; public experimental artifact; promotion not established.
"""

    return card


def build_publish_directory(
    model_card: str,
) -> None:
    log("\n=== BUILD HUGGING FACE MODEL DIRECTORY ===")

    if PUBLISH.exists():
        shutil.rmtree(PUBLISH)

    PUBLISH.mkdir(parents=True, exist_ok=True)

    # Root adapter is seed 11, making the repository directly loadable.
    for item in RUN1_ADAPTER.iterdir():
        target = PUBLISH / item.name

        if item.is_dir():
            shutil.copytree(
                item,
                target,
                dirs_exist_ok=True,
            )
        else:
            shutil.copy2(item, target)

    adapters_dir = PUBLISH / "adapters"
    adapters_dir.mkdir(parents=True, exist_ok=True)

    for seed in SEEDS:
        source = adapter_path_for_seed(seed)
        target = adapters_dir / f"seed-{seed:03d}"

        shutil.copytree(
            source,
            target,
            dirs_exist_ok=True,
        )

    shutil.copytree(
        EVIDENCE,
        PUBLISH / "evidence",
        dirs_exist_ok=True,
    )

    (PUBLISH / "README.md").write_text(
        model_card,
        encoding="utf-8",
        newline="\n",
    )

    publish_manifest = {
        "schema": "szl.huggingface-publication/v1",
        "repo_id": HF_REPO,
        "base_model": BASE_MODEL,
        "default_adapter": "seed-011",
        "adapters": [
            f"seed-{seed:03d}"
            for seed in SEEDS
        ],
        "release_gate": "11/12",
        "release_status": "BLOCKED",
        "promotion_status": "NOT_PROMOTABLE",
        "publication_status": "PUBLIC_EXPERIMENTAL_ARTIFACT",
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    write_json(
        PUBLISH / "publication-receipt.json",
        publish_manifest,
    )


def publish_to_hub() -> str:
    log("\n=== PUBLISH MODEL TO HUGGING FACE ===")

    from huggingface_hub import HfApi

    token = os.environ.get("HF_TOKEN") or None
    api = HfApi(token=token)

    repo_url = api.create_repo(
        repo_id=HF_REPO,
        repo_type="model",
        private=False,
        exist_ok=True,
        token=token,
    )

    log(f"Repository ready: {repo_url}")

    commit_url = api.upload_folder(
        folder_path=str(PUBLISH),
        repo_id=HF_REPO,
        repo_type="model",
        commit_message=(
            "Publish five-seed measured triage LoRA study "
            "with frozen evaluation and receipts"
        ),
        token=token,
    )

    info = api.model_info(
        repo_id=HF_REPO,
        token=token,
    )

    publication_receipt = {
        "schema": "szl.huggingface-publication-result/v1",
        "repo_id": HF_REPO,
        "repo_url": f"https://huggingface.co/{HF_REPO}",
        "commit_url": str(commit_url),
        "hub_sha": getattr(info, "sha", None),
        "private": getattr(info, "private", None),
        "release_gate": "11/12",
        "release_status": "BLOCKED",
        "promotion_status": "NOT_PROMOTABLE",
        "publication_status": "PUBLISHED",
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    write_json(
        EVIDENCE / "huggingface-publication.json",
        publication_receipt,
    )

    # Also put the final publication receipt onto the Hub.
    api.upload_file(
        path_or_fileobj=str(
            EVIDENCE / "huggingface-publication.json"
        ),
        path_in_repo=(
            "evidence/huggingface-publication.json"
        ),
        repo_id=HF_REPO,
        repo_type="model",
        commit_message=(
            "Record verified Hugging Face publication receipt"
        ),
        token=token,
    )

    log(json.dumps(publication_receipt, indent=2))

    return publication_receipt["repo_url"]


def commit_github_evidence() -> str:
    log("\n=== COMMIT AND PUSH GITHUB EVIDENCE ===")

    run(
        [
            "git",
            "add",
            "scripts/train_eval_publish.py",
            "evidence/five-seed-study",
        ]
    )

    run(["git", "diff", "--cached", "--check"])

    staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=str(ROOT),
    ).returncode

    if staged != 0:
        run(
            [
                "git",
                "commit",
                "-m",
                (
                    "Publish five-seed triage LoRA study "
                    "with frozen evaluation"
                ),
            ]
        )
    else:
        log("No new staged evidence to commit")

    branch = command_output(
        ["git", "branch", "--show-current"]
    )

    if not branch:
        raise RuntimeError("Detached HEAD; cannot push evidence")

    run(["git", "push", "estate", branch])

    existing_tags = command_output(["git", "tag", "--list", STUDY_TAG])

    if not existing_tags:
        run(
            [
                "git",
                "tag",
                "-a",
                STUDY_TAG,
                "-m",
                (
                    "Five-seed training and frozen evaluation "
                    "measured; public artifact published; "
                    "promotion not established"
                ),
            ]
        )
    else:
        tag_target = command_output(
            ["git", "rev-list", "-n", "1", STUDY_TAG]
        )
        head_target = command_output(
            ["git", "rev-parse", "HEAD"]
        )

        if tag_target != head_target:
            raise RuntimeError(
                f"{STUDY_TAG} already exists on another commit"
            )

    run(["git", "push", "estate", STUDY_TAG])

    return branch


def main() -> None:
    started = time.time()

    os.environ["SZL_ALLOW_HUB_PUSH"] = "0"
    os.environ.setdefault(
        "TOKENIZERS_PARALLELISM",
        "false",
    )
    os.environ.setdefault(
        "PYTORCH_CUDA_ALLOC_CONF",
        "expandable_segments:True",
    )

    preflight()
    _, held_records = freeze_split()
    receipts = train_new_seeds()
    metrics = run_all_evaluations(held_records)
    aggregate = aggregate_results(metrics)
    adapter_index = collect_evidence(
        receipts,
        aggregate,
    )

    model_card = build_model_card(
        metrics,
        aggregate,
        adapter_index,
    )

    build_publish_directory(model_card)
    hub_url = publish_to_hub()
    branch = commit_github_evidence()

    elapsed = round(time.time() - started, 1)

    final = {
        "schema": "szl.study-completion/v1",
        "state": "COMPLETE",
        "seconds": elapsed,
        "seeds": SEEDS,
        "hub_url": hub_url,
        "github_branch": branch,
        "github_tag": STUDY_TAG,
        "release_gate": "11/12",
        "release_status": "BLOCKED",
        "promotion_status": "NOT_PROMOTABLE",
        "publication_status": "PUBLISHED",
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    write_json(
        STUDY / "completion.json",
        final,
    )

    log("\n" + "=" * 72)
    log("FIVE-SEED TRAINING, EVALUATION, AND PUBLICATION COMPLETE")
    log("=" * 72)
    log(f"Hugging Face: {hub_url}")
    log(f"GitHub tag: {STUDY_TAG}")
    log("Adapters: seed 11, 23, 37, 53, 71")
    log("Release gate: BLOCKED at 11/12")
    log("Promotion: NOT_PROMOTABLE")
    log("Publication: PUBLISHED")
    log("=" * 72)


if __name__ == "__main__":
    main()