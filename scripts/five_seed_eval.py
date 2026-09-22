from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import re
import statistics
import time
from pathlib import Path

BASE_MODEL = "unsloth/Qwen3.5-0.8B"


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def sha256_file(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def text_of(row):
    for key in ("input", "text", "prompt"):
        if isinstance(row.get(key), str):
            return row[key]
    return json.dumps(row, ensure_ascii=False)


def family_key(text):
    normalized = re.sub(r"[^a-z ]", " ", text.lower())
    prefix = " ".join(normalized.split()[:8])
    return hashlib.sha1(prefix.encode()).hexdigest()[:10]


def row_id(row):
    return hashlib.sha256(canonical(row).encode()).hexdigest()


def choose_corpus():
    choices = (
        Path("output/triage_distill_v0.5.0.jsonl"),
        Path("output/triage_distill.jsonl"),
    )
    for path in choices:
        if path.exists():
            return path
    raise SystemExit("REFUSE: no distillation corpus found")


def split_rows(rows):
    families = {}
    for row in rows:
        key = family_key(text_of(row))
        families.setdefault(key, []).append(row)

    keys = sorted(families)
    cut = int(len(keys) * 0.8)

    train = [row for key in keys[:cut] for row in families[key]]
    held = [row for key in keys[cut:] for row in families[key]]

    return train, held, keys[:cut], keys[cut:]


def freeze(study_root: Path):
    frozen = study_root / "frozen"
    frozen.mkdir(parents=True, exist_ok=True)

    corpus = choose_corpus()
    rows = [
        json.loads(line)
        for line in corpus.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]

    train, held, train_families, held_families = split_rows(rows)

    if len(train) != 515 or len(held) != 113:
        raise SystemExit(
            f"REFUSE: expected frozen 515/113 split; got {len(train)}/{len(held)}"
        )

    train_family_set = set(train_families)
    held_family_set = set(held_families)

    if train_family_set & held_family_set:
        raise SystemExit("REFUSE: family overlap detected")

    train_records = [
        {
            "row_id": row_id(row),
            "family": family_key(text_of(row)),
            "row": row,
        }
        for row in train
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
            "row": row,
        }
        for row in held
    ]

    train_path = frozen / "train.jsonl"
    held_path = frozen / "held.jsonl"

    train_path.write_text(
        "\n".join(canonical(record) for record in train_records) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    held_path.write_text(
        "\n".join(canonical(record) for record in held_records) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    manifest = {
        "schema": "szl.five-seed-frozen-split/v1",
        "run1_tag": "triage-lora-run1",
        "run1_commit": "427a70eb0804d814bf32d2cfc2713e230e468691",
        "base_model": BASE_MODEL,
        "corpus": str(corpus),
        "corpus_sha256": sha256_file(corpus),
        "rows": len(rows),
        "families": len(train_families) + len(held_families),
        "train_rows": len(train),
        "held_rows": len(held),
        "train_families": len(train_families),
        "held_families": len(held_families),
        "train_manifest_sha256": sha256_file(train_path),
        "held_manifest_sha256": sha256_file(held_path),
        "split_method": "sorted template-family hash; first 80 percent train",
        "seeds": [11, 23, 37, 53, 71],
        "status": "FROZEN",
        "promotion_status": "NOT_PROMOTABLE",
        "warning": (
            "This manifest freezes evaluation identity. It does not resolve "
            "the contamination verdict or establish promotion."
        ),
    }

    (frozen / "experiment_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
        newline="\n",
    )

    print(json.dumps(manifest, indent=2))


def strict_json(raw):
    try:
        value = json.loads(raw.strip())
    except Exception:
        return None

    if not isinstance(value, dict):
        return None

    if not {"label", "state", "evidence"}.issubset(value):
        return None

    if not isinstance(value.get("evidence"), list):
        return None

    return value


def load_target(adapter: str | None):
    import torch
    from unsloth import FastLanguageModel

    model_name = adapter if adapter else BASE_MODEL

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=1024,
        load_in_4bit=False,
        dtype=torch.bfloat16,
    )

    FastLanguageModel.for_inference(model)
    model.eval()
    return model, tokenizer


def render_prompt(tokenizer, prompt):
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


def generate(model, tokenizer, prompt):
    import torch

    rendered = render_prompt(tokenizer, prompt)
    inputs = tokenizer(rendered, return_tensors="pt")

    device = next(model.parameters()).device
    inputs = {key: value.to(device) for key, value in inputs.items()}

    started = time.perf_counter()

    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=192,
            do_sample=False,
            use_cache=True,
            pad_token_id=tokenizer.eos_token_id,
        )

    latency = time.perf_counter() - started
    prompt_length = inputs["input_ids"].shape[1]

    raw = tokenizer.decode(
        output[0][prompt_length:],
        skip_special_tokens=True,
    )

    return raw, latency


def safe_ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def evaluate_target(study_root: Path, name: str, adapter: str | None):
    import torch

    frozen = study_root / "frozen"
    evaluation = study_root / "evaluation"
    evaluation.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(
        (frozen / "experiment_manifest.json").read_text(encoding="utf-8-sig")
    )

    held_path = frozen / "held.jsonl"

    if sha256_file(held_path) != manifest["held_manifest_sha256"]:
        raise SystemExit("REFUSE: frozen held manifest changed")

    records = [
        json.loads(line)
        for line in held_path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]

    if len(records) != 113:
        raise SystemExit(f"REFUSE: expected 113 held rows; got {len(records)}")

    if adapter:
        adapter_path = Path(adapter)
        if not adapter_path.exists():
            raise SystemExit(f"REFUSE: adapter absent: {adapter_path}")

    model, tokenizer = load_target(adapter)

    predictions = []
    counts = {
        "rows": 0,
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

    for index, record in enumerate(records, start=1):
        raw, latency = generate(model, tokenizer, record["prompt"])
        parsed = strict_json(raw)
        gold = record["target"]

        if parsed is None:
            predicted_label = None
            predicted_state = None
            predicted_evidence = []
        else:
            counts["strict_json"] += 1
            predicted_label = parsed.get("label")
            predicted_state = parsed.get("state")
            predicted_evidence = parsed.get("evidence", [])

        label_ok = predicted_label == gold.get("label")
        state_ok = predicted_state == gold.get("state")
        joint_ok = label_ok and state_ok
        evidence_exact = predicted_evidence == gold.get("evidence", [])

        grounded_flags = [
            isinstance(span, str) and span in record["prompt"]
            for span in predicted_evidence
        ]

        counts["rows"] += 1
        counts["label_exact"] += int(label_ok)
        counts["state_exact"] += int(state_ok)
        counts["joint_exact"] += int(joint_ok)
        counts["target_evidence_exact"] += int(evidence_exact)
        counts["predicted_evidence_spans"] += len(grounded_flags)
        counts["grounded_evidence_spans"] += sum(grounded_flags)

        if gold.get("state") == "REVIEW":
            counts["refusal_rows"] += 1
            if predicted_state == "REVIEW":
                counts["refusal_fidelity"] += 1
            else:
                counts["false_label_on_refusal"] += 1

        predictions.append(
            {
                "row_id": record["row_id"],
                "family": record["family"],
                "gold": gold,
                "raw_output": raw,
                "parsed": parsed,
                "label_exact": label_ok,
                "state_exact": state_ok,
                "joint_exact": joint_ok,
                "target_evidence_exact": evidence_exact,
                "grounded_evidence_flags": grounded_flags,
                "latency_seconds": latency,
            }
        )

        print(f"{name}: {index}/113", flush=True)

    failures = [
        prediction
        for prediction in predictions
        if (
            prediction["parsed"] is None
            or not prediction["joint_exact"]
            or not all(prediction["grounded_evidence_flags"])
        )
    ]

    prediction_path = evaluation / f"predictions-{name}.jsonl"
    failure_path = evaluation / f"failures-{name}.jsonl"

    prediction_path.write_text(
        "\n".join(canonical(item) for item in predictions) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    failure_path.write_text(
        (
            "\n".join(canonical(item) for item in failures) + "\n"
            if failures
            else ""
        ),
        encoding="utf-8",
        newline="\n",
    )

    metrics = {
        "schema": "szl.frozen-held-evaluation/v1",
        "name": name,
        "base_model": BASE_MODEL,
        "adapter": adapter,
        "held_manifest_sha256": manifest["held_manifest_sha256"],
        "decoding": {
            "do_sample": False,
            "max_new_tokens": 192,
            "repair_malformed_json": False,
        },
        **counts,
        "strict_json_rate": safe_ratio(counts["strict_json"], counts["rows"]),
        "label_accuracy": safe_ratio(counts["label_exact"], counts["rows"]),
        "state_accuracy": safe_ratio(counts["state_exact"], counts["rows"]),
        "joint_accuracy": safe_ratio(counts["joint_exact"], counts["rows"]),
        "target_evidence_exact_rate": safe_ratio(
            counts["target_evidence_exact"], counts["rows"]
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
            item["latency_seconds"] for item in predictions
        ),
        "failure_rows": len(failures),
        "predictions_sha256": sha256_file(prediction_path),
        "failures_sha256": sha256_file(failure_path),
        "promotion_status": "NOT_PROMOTABLE",
        "promotion_note": (
            "Evaluation does not override the contamination verdict. "
            "Promotion remains derived from all release gates."
        ),
    }

    (evaluation / f"metrics-{name}.json").write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
        newline="\n",
    )

    print(json.dumps(metrics, indent=2))

    del model
    del tokenizer
    gc.collect()
    torch.cuda.empty_cache()


def aggregate(study_root: Path):
    evaluation = study_root / "evaluation"

    names = [
        "base",
        "seed-011",
        "seed-023",
        "seed-037",
        "seed-053",
        "seed-071",
    ]

    metrics = []

    for name in names:
        path = evaluation / f"metrics-{name}.json"
        if not path.exists():
            raise SystemExit(f"REFUSE: missing evaluation receipt {path}")
        metrics.append(json.loads(path.read_text(encoding="utf-8-sig")))

    adapter_metrics = [
        metric for metric in metrics if metric["name"].startswith("seed-")
    ]

    scalar_keys = [
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

    for key in scalar_keys:
        values = [
            metric[key]
            for metric in adapter_metrics
            if metric.get(key) is not None
        ]

        summary[key] = {
            "n": len(values),
            "mean": statistics.fmean(values) if values else None,
            "sample_std": statistics.stdev(values) if len(values) > 1 else None,
            "min": min(values) if values else None,
            "max": max(values) if values else None,
        }

    aggregate_receipt = {
        "schema": "szl.five-seed-aggregate/v1",
        "base_model": BASE_MODEL,
        "seeds": [11, 23, 37, 53, 71],
        "held_rows": 113,
        "targets": metrics,
        "five_seed_summary": summary,
        "release_status": "BLOCKED",
        "promotion_status": "NOT_PROMOTABLE",
        "reason": (
            "Training and frozen evaluation are measured, but the existing "
            "contamination and release gates remain authoritative."
        ),
    }

    (evaluation / "aggregate_metrics.json").write_text(
        json.dumps(aggregate_receipt, indent=2),
        encoding="utf-8",
        newline="\n",
    )

    csv_path = evaluation / "metrics.csv"

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

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for metric in metrics:
            writer.writerow({field: metric.get(field) for field in fields})

    print(json.dumps(aggregate_receipt, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--study-root", type=Path, required=True)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--aggregate", action="store_true")
    parser.add_argument("--name")
    parser.add_argument("--adapter")
    args = parser.parse_args()

    if args.freeze:
        freeze(args.study_root)
        return

    if args.aggregate:
        aggregate(args.study_root)
        return

    if not args.name:
        raise SystemExit("REFUSE: --name is required for evaluation")

    evaluate_target(args.study_root, args.name, args.adapter)


if __name__ == "__main__":
    main()