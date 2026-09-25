# =============================================================================
# SZL TYPESAFE TRIAGE — FIVE-SEED TRAIN + FROZEN EVALUATION + EVIDENCE PUSH
# Paste this entire block into ADMINISTRATOR POWERSHELL.
# =============================================================================

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Repo = "C:\Users\steph\szl-typesafe-triage"
$ExpectedRun1Commit = "427a70eb0804d814bf32d2cfc2713e230e468691"
$Seeds = @(23, 37, 53, 71)
$BaseModel = "unsloth/Qwen3.5-0.8B"

# -----------------------------------------------------------------------------
# ADMINISTRATION AND REPOSITORY PREFLIGHT
# -----------------------------------------------------------------------------

$admin = ([Security.Principal.WindowsPrincipal](
    [Security.Principal.WindowsIdentity]::GetCurrent()
)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $admin) {
    throw "REFUSE: Open PowerShell as Administrator, then paste the block again."
}

if (-not (Test-Path $Repo)) {
    throw "REFUSE: Repository not found at $Repo"
}

Set-Location $Repo

if (-not (Test-Path ".git")) {
    throw "REFUSE: $Repo is not a Git repository."
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "REFUSE: Missing .venv\Scripts\python.exe"
}

$Python = (Resolve-Path ".venv\Scripts\python.exe").Path

if (-not (Test-Path "scripts\train_lora.py")) {
    throw "REFUSE: scripts\train_lora.py is missing."
}

if (-not (Test-Path "out\train\adapter\adapter_model.safetensors")) {
    throw "REFUSE: Immutable run-1 adapter is missing."
}

if (-not (Test-Path "out\train\training_receipt.json")) {
    throw "REFUSE: Immutable run-1 receipt is missing."
}

$trackedChanges = git status --porcelain --untracked-files=no
if ($LASTEXITCODE -ne 0) {
    throw "REFUSE: git status failed."
}
if ($trackedChanges) {
    Write-Host $trackedChanges -ForegroundColor Yellow
    throw "REFUSE: Commit or restore existing tracked changes before starting."
}

$tagCommit = (git rev-list -n 1 triage-lora-run1).Trim()
if ($tagCommit -ne $ExpectedRun1Commit) {
    throw "REFUSE: triage-lora-run1 resolves to $tagCommit, expected $ExpectedRun1Commit"
}

$currentBranch = (git branch --show-current).Trim()
if (-not $currentBranch) {
    throw "REFUSE: Detached HEAD. Checkout the intended working branch first."
}

$estateRemote = git remote get-url estate
if ($LASTEXITCODE -ne 0 -or -not $estateRemote) {
    throw "REFUSE: Git remote 'estate' is missing."
}

gh auth status
if ($LASTEXITCODE -ne 0) {
    throw "REFUSE: GitHub CLI is not authenticated."
}
gh auth setup-git
if ($LASTEXITCODE -ne 0) {
    throw "REFUSE: Could not configure Git to use GitHub CLI authentication."
}

# Never let these study scripts write to Hugging Face.
$env:SZL_ALLOW_HUB_PUSH = "0"
$env:TOKENIZERS_PARALLELISM = "false"
$env:PYTORCH_CUDA_ALLOC_CONF = "expandable_segments:True"

# -----------------------------------------------------------------------------
# CUDA PREFLIGHT — FILE-BASED TO AVOID NATIVE ARGUMENT QUOTING
# -----------------------------------------------------------------------------

$PreflightFile = Join-Path $env:TEMP "szl_cuda_preflight.py"

$PreflightSource = @"
import json
import sys

try:
    import unsloth
    import torch
except Exception as exc:
    raise SystemExit(
        "REFUSE: ML stack import failed: "
        + type(exc).__name__
        + ": "
        + str(exc)
    )

if not torch.cuda.is_available():
    raise SystemExit("REFUSE: CUDA is unavailable")

capability = torch.cuda.get_device_capability()
required_arch = "sm_" + str(capability[0]) + str(capability[1])
available_arches = torch.cuda.get_arch_list()

if required_arch not in available_arches:
    raise SystemExit(
        "REFUSE: GPU requires "
        + required_arch
        + "; installed wheel contains "
        + repr(available_arches)
    )

print(json.dumps({
    "python": sys.version,
    "torch": torch.__version__,
    "cuda": torch.version.cuda,
    "device": torch.cuda.get_device_name(0),
    "capability": list(capability),
    "required_arch": required_arch,
    "available_arches": available_arches,
    "arch_present": True,
    "unsloth": getattr(unsloth, "__version__", "unknown"),
}, indent=2))
"@

try {
    [IO.File]::WriteAllText(
        $PreflightFile,
        $PreflightSource,
        [Text.UTF8Encoding]::new($false)
    )

    & $Python $PreflightFile
    $PreflightExit = $LASTEXITCODE
}
finally {
    Remove-Item $PreflightFile -Force -ErrorAction SilentlyContinue
}

if ($PreflightExit -ne 0) {
    throw "REFUSE: CUDA/Unsloth preflight genuinely failed."
}
# -----------------------------------------------------------------------------
# CREATE THE FROZEN EVALUATOR
# -----------------------------------------------------------------------------

$EvaluatorSource = @'
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
'@

[IO.File]::WriteAllText(
    (Join-Path $Repo "scripts\five_seed_eval.py"),
    $EvaluatorSource,
    [Text.UTF8Encoding]::new($false)
)

# -----------------------------------------------------------------------------
# CREATE THE REPRODUCIBLE POWERSHELL CONTROLLER
# -----------------------------------------------------------------------------

$RunnerSource = @'
param(
    [string]$Repo = "C:\Users\steph\szl-typesafe-triage"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Set-Location $Repo

$Python = (Resolve-Path ".venv\Scripts\python.exe").Path
$Study = Join-Path $Repo "out\train\study"
$Control = Join-Path $Study "control"
$Evidence = Join-Path $Repo "evidence\five-seed-study"
$Trainer = Join-Path $Repo "scripts\train_lora.py"
$Evaluator = Join-Path $Repo "scripts\five_seed_eval.py"
$Seeds = @(23, 37, 53, 71)

New-Item -ItemType Directory -Force $Study | Out-Null
New-Item -ItemType Directory -Force $Control | Out-Null
New-Item -ItemType Directory -Force $Evidence | Out-Null

function Refuse([string]$Message) {
    throw "REFUSE: $Message"
}

function Invoke-Python {
    param(
        [string[]]$Arguments,
        [string]$LogPath
    )

    & $Python @Arguments 2>&1 | Tee-Object -FilePath $LogPath
    $code = $LASTEXITCODE

    if ($code -ne 0) {
        Refuse "Python exited with code $code. Read $LogPath"
    }
}

function Test-CorpusHash {
    $manifestPath = Join-Path $Study "frozen\experiment_manifest.json"

    if (-not (Test-Path $manifestPath)) {
        Refuse "frozen experiment manifest is absent"
    }

    $manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
    $corpusPath = Join-Path $Repo $manifest.corpus

    if (-not (Test-Path $corpusPath)) {
        Refuse "frozen corpus is absent: $corpusPath"
    }

    $actual = (Get-FileHash $corpusPath -Algorithm SHA256).Hash.ToLowerInvariant()

    if ($actual -ne $manifest.corpus_sha256.ToLowerInvariant()) {
        Refuse "corpus changed after the split was frozen"
    }
}

Write-Host "=== FREEZE FAMILY SPLIT ===" -ForegroundColor Cyan

Invoke-Python `
    -Arguments @(
        $Evaluator,
        "--study-root", $Study,
        "--freeze"
    ) `
    -LogPath (Join-Path $Study "freeze.log")

Test-CorpusHash

Write-Host "=== EVALUATE UNTOUCHED BASE MODEL ===" -ForegroundColor Cyan

$baseMetrics = Join-Path $Study "evaluation\metrics-base.json"
if (-not (Test-Path $baseMetrics)) {
    Invoke-Python `
        -Arguments @(
            $Evaluator,
            "--study-root", $Study,
            "--name", "base"
        ) `
        -LogPath (Join-Path $Study "evaluation-base.log")
}
else {
    Write-Host "Base evaluation already exists; preserving it." -ForegroundColor Yellow
}

Write-Host "=== EVALUATE IMMUTABLE RUN 1 / SEED 11 ===" -ForegroundColor Cyan

$run1Adapter = Join-Path $Repo "out\train\adapter"
$run1Metrics = Join-Path $Study "evaluation\metrics-seed-011.json"

if (-not (Test-Path $run1Metrics)) {
    Invoke-Python `
        -Arguments @(
            $Evaluator,
            "--study-root", $Study,
            "--name", "seed-011",
            "--adapter", $run1Adapter
        ) `
        -LogPath (Join-Path $Study "evaluation-seed-011.log")
}
else {
    Write-Host "Seed 11 evaluation already exists; preserving it." -ForegroundColor Yellow
}

$originalTrainer = [IO.File]::ReadAllText($Trainer).Replace("`r`n", "`n")

if (-not $originalTrainer.Contains('OUT = Path("out/train"); OUT.mkdir(parents=True, exist_ok=True)')) {
    Refuse "trainer OUT assignment no longer matches the tagged run"
}
if (-not $originalTrainer.Contains("random_state=11")) {
    Refuse "trainer random_state marker is absent"
}
if (-not $originalTrainer.Contains("seed=11")) {
    Refuse "trainer seed marker is absent"
}
if (-not $originalTrainer.Contains('"seed": 11')) {
    Refuse "trainer receipt seed marker is absent"
}

foreach ($seed in $Seeds) {
    Test-CorpusHash

    $name = "seed-{0:d3}" -f $seed
    $relativeOutput = "out/train/study/$name"
    $runDirectory = Join-Path $Repo $relativeOutput
    $receiptPath = Join-Path $runDirectory "training_receipt.json"
    $adapterPath = Join-Path $runDirectory "adapter"
    $adapterFile = Join-Path $adapterPath "adapter_model.safetensors"
    $metricsPath = Join-Path $Study "evaluation\metrics-$name.json"
    $patchedTrainer = Join-Path $Control "train_$name.py"

    Write-Host "=== TRAIN $name ===" -ForegroundColor Cyan

    if (Test-Path $receiptPath) {
        $existingReceipt = Get-Content $receiptPath -Raw | ConvertFrom-Json

        if (
            $existingReceipt.state -ne "MEASURED" -or
            $existingReceipt.binding_check -ne "PASS" -or
            [int]$existingReceipt.hyperparameters.seed -ne $seed -or
            -not (Test-Path $adapterFile)
        ) {
            Refuse "$name is partial or invalid; no automatic overwrite permitted"
        }

        Write-Host "$name already measured; preserving adapter." -ForegroundColor Yellow
    }
    else {
        if (Test-Path $runDirectory) {
            $existingItems = Get-ChildItem $runDirectory -Force -ErrorAction SilentlyContinue
            if ($existingItems) {
                Refuse "$name has partial files; inspect them before retrying"
            }
        }

        New-Item -ItemType Directory -Force $runDirectory | Out-Null

        $patched = $originalTrainer.Replace(
            'OUT = Path("out/train"); OUT.mkdir(parents=True, exist_ok=True)',
            ('OUT = Path("' + $relativeOutput + '"); OUT.mkdir(parents=True, exist_ok=True)')
        )

        $patched = $patched.Replace(
            "random_state=11",
            "random_state=$seed"
        )

        $patched = $patched.Replace(
            "seed=11",
            "seed=$seed"
        )

        $patched = $patched.Replace(
            '"seed": 11',
            ('"seed": ' + $seed)
        )

        if ($patched -eq $originalTrainer) {
            Refuse "trainer patch produced no changes for $name"
        }

        [IO.File]::WriteAllText(
            $patchedTrainer,
            $patched,
            [Text.UTF8Encoding]::new($false)
        )

        Invoke-Python `
            -Arguments @($patchedTrainer) `
            -LogPath (Join-Path $runDirectory "training.log")

        if (-not (Test-Path $receiptPath)) {
            Refuse "$name did not produce training_receipt.json"
        }

        if (-not (Test-Path $adapterFile)) {
            Refuse "$name did not produce adapter_model.safetensors"
        }

        $receipt = Get-Content $receiptPath -Raw | ConvertFrom-Json

        if ($receipt.state -ne "MEASURED") {
            Refuse "$name state is $($receipt.state), expected MEASURED"
        }

        if ($receipt.binding_check -ne "PASS") {
            Refuse "$name binding check failed: $($receipt.binding_check)"
        }

        if ([int]$receipt.hyperparameters.seed -ne $seed) {
            Refuse "$name receipt recorded the wrong seed"
        }
    }

    Test-CorpusHash

    Write-Host "=== EVALUATE $name ===" -ForegroundColor Cyan

    if (-not (Test-Path $metricsPath)) {
        Invoke-Python `
            -Arguments @(
                $Evaluator,
                "--study-root", $Study,
                "--name", $name,
                "--adapter", $adapterPath
            ) `
            -LogPath (Join-Path $Study "evaluation-$name.log")
    }
    else {
        Write-Host "$name evaluation already exists; preserving it." -ForegroundColor Yellow
    }
}

Write-Host "=== AGGREGATE FIVE-SEED STUDY ===" -ForegroundColor Cyan

Invoke-Python `
    -Arguments @(
        $Evaluator,
        "--study-root", $Study,
        "--aggregate"
    ) `
    -LogPath (Join-Path $Study "aggregate.log")

# -----------------------------------------------------------------------------
# BUILD COMMITTABLE EVIDENCE PACKAGE — NO MODEL WEIGHTS
# -----------------------------------------------------------------------------

Write-Host "=== BUILD EVIDENCE PACKAGE ===" -ForegroundColor Cyan

if (Test-Path $Evidence) {
    Remove-Item $Evidence -Recurse -Force
}
New-Item -ItemType Directory -Force $Evidence | Out-Null
New-Item -ItemType Directory -Force (Join-Path $Evidence "training") | Out-Null
New-Item -ItemType Directory -Force (Join-Path $Evidence "evaluation") | Out-Null
New-Item -ItemType Directory -Force (Join-Path $Evidence "frozen") | Out-Null

Copy-Item `
    (Join-Path $Study "frozen\*") `
    (Join-Path $Evidence "frozen") `
    -Recurse -Force

Copy-Item `
    (Join-Path $Study "evaluation\*") `
    (Join-Path $Evidence "evaluation") `
    -Recurse -Force

Copy-Item `
    "out\train\training_receipt.json" `
    (Join-Path $Evidence "training\training_receipt-seed-011.json") `
    -Force

$adapterIndex = @()

$run1Hash = (
    Get-FileHash "out\train\adapter\adapter_model.safetensors" -Algorithm SHA256
).Hash

$adapterIndex += [ordered]@{
    seed = 11
    tag = "triage-lora-run1"
    commit = "427a70eb0804d814bf32d2cfc2713e230e468691"
    local_path = "out/train/adapter"
    adapter_sha256 = $run1Hash
    promotion_status = "NOT_PROMOTABLE"
}

foreach ($seed in $Seeds) {
    $name = "seed-{0:d3}" -f $seed
    $sourceReceipt = Join-Path $Study "$name\training_receipt.json"
    $targetReceipt = Join-Path $Evidence "training\training_receipt-$name.json"
    $adapterFile = Join-Path $Study "$name\adapter\adapter_model.safetensors"

    Copy-Item $sourceReceipt $targetReceipt -Force

    $receipt = Get-Content $sourceReceipt -Raw | ConvertFrom-Json
    $adapterHash = (Get-FileHash $adapterFile -Algorithm SHA256).Hash

    $adapterIndex += [ordered]@{
        seed = $seed
        local_path = "out/train/study/$name/adapter"
        adapter_sha256 = $adapterHash
        final_training_loss = $receipt.final_training_loss
        seconds = $receipt.seconds
        binding_check = $receipt.binding_check
        promotion_status = $receipt.promotion_status
    }
}

$adapterIndex | ConvertTo-Json -Depth 10 |
    Set-Content `
        (Join-Path $Evidence "adapter-index.json") `
        -Encoding utf8NoBOM

$environmentReceipt = [ordered]@{
    schema = "szl.five-seed-environment/v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    repository_commit = (git rev-parse HEAD).Trim()
    branch = (git branch --show-current).Trim()
    python = (& $Python --version 2>&1 | Out-String).Trim()
    pip_freeze = @(& $Python -m pip freeze)
    nvidia_smi = @(nvidia-smi)
    release_status = "BLOCKED"
    promotion_status = "NOT_PROMOTABLE"
}

$environmentReceipt | ConvertTo-Json -Depth 10 |
    Set-Content `
        (Join-Path $Evidence "environment-receipt.json") `
        -Encoding utf8NoBOM

$studyReadme = @"
# TypeSafe Triage five-seed measured study

Seeds: 11, 23, 37, 53, 71.

The corpus split was frozen by template family before the additional runs.
The untouched base model and every adapter were evaluated on the identical
113-row held-family manifest using greedy decoding and no malformed-JSON repair.

This directory contains:

- frozen train and held manifests;
- all five training receipts;
- base and adapter evaluation receipts;
- complete raw predictions;
- complete failure files;
- aggregate metrics and CSV export;
- adapter hashes without publishing gated model weights;
- environment and package evidence.

Training and evaluation are measured. The existing contamination verdict
remains attached. Release remains BLOCKED and promotion remains
NOT_PROMOTABLE unless separate release gates establish otherwise.
"@

[IO.File]::WriteAllText(
    (Join-Path $Evidence "README.md"),
    $studyReadme,
    [Text.UTF8Encoding]::new($false)
)

# -----------------------------------------------------------------------------
# VALIDATE EVIDENCE BEFORE GIT COMMIT
# -----------------------------------------------------------------------------

Write-Host "=== VALIDATE EVIDENCE ===" -ForegroundColor Cyan

$aggregatePath = Join-Path $Evidence "evaluation\aggregate_metrics.json"
if (-not (Test-Path $aggregatePath)) {
    Refuse "aggregate metrics are missing"
}

$aggregate = Get-Content $aggregatePath -Raw | ConvertFrom-Json

if ($aggregate.held_rows -ne 113) {
    Refuse "aggregate held-row count is not 113"
}

if ($aggregate.targets.Count -ne 6) {
    Refuse "expected base plus five adapter evaluation targets"
}

if ($aggregate.promotion_status -ne "NOT_PROMOTABLE") {
    Refuse "promotion boundary changed unexpectedly"
}

# Ensure no individual file would violate GitHub's ordinary 100 MB file limit.
Get-ChildItem $Evidence -Recurse -File | ForEach-Object {
    if ($_.Length -ge 95MB) {
        Refuse "evidence file is too large for ordinary Git: $($_.FullName)"
    }
}

# -----------------------------------------------------------------------------
# COMMIT AND PUSH CODE + EVIDENCE
# -----------------------------------------------------------------------------

Write-Host "=== COMMIT AND PUSH MEASURED STUDY ===" -ForegroundColor Cyan

git add `
    scripts/five_seed_eval.py `
    evidence/five-seed-study

if ($LASTEXITCODE -ne 0) {
    Refuse "git add failed"
}

git diff --cached --check
if ($LASTEXITCODE -ne 0) {
    Refuse "staged diff validation failed"
}

$staged = git diff --cached --name-only

if ($staged) {
    git commit -m "Measure five-seed triage study on frozen family holdout"
    if ($LASTEXITCODE -ne 0) {
        Refuse "git commit failed"
    }
}
else {
    Write-Host "No new study changes to commit." -ForegroundColor Yellow
}

$branch = (git branch --show-current).Trim()
if (-not $branch) {
    Refuse "branch became detached"
}

git push estate $branch
if ($LASTEXITCODE -ne 0) {
    Refuse "branch push failed; local evidence remains intact"
}

$studyTag = "triage-lora-study5-measured"
$existingTag = git tag --list $studyTag

if (-not $existingTag) {
    git tag -a $studyTag -m "Five-seed training and frozen held-family evaluation measured; promotion not established"
    if ($LASTEXITCODE -ne 0) {
        Refuse "study tag creation failed"
    }
}
else {
    $tagTarget = (git rev-list -n 1 $studyTag).Trim()
    $headTarget = (git rev-parse HEAD).Trim()

    if ($tagTarget -ne $headTarget) {
        Refuse "$studyTag already exists on a different commit"
    }
}

git push estate $studyTag
if ($LASTEXITCODE -ne 0) {
    Refuse "study tag push failed; do not move the tag"
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "FIVE-SEED TRAINING AND FROZEN EVALUATION COMPLETE" -ForegroundColor Green
Write-Host "Evidence: evidence\five-seed-study" -ForegroundColor Green
Write-Host "Tag: triage-lora-study5-measured" -ForegroundColor Green
Write-Host "Release: BLOCKED" -ForegroundColor Yellow
Write-Host "Promotion: NOT_PROMOTABLE" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Green
'@

[IO.File]::WriteAllText(
    (Join-Path $Repo "scripts\run_five_seed_study.ps1"),
    $RunnerSource,
    [Text.UTF8Encoding]::new($false)
)

# Syntax-check the evaluator before beginning GPU work.
& $Python -m py_compile "scripts\five_seed_eval.py"
if ($LASTEXITCODE -ne 0) {
    throw "REFUSE: evaluator syntax validation failed."
}

# -----------------------------------------------------------------------------
# RUN EVERYTHING
# -----------------------------------------------------------------------------

Write-Host ""
Write-Host "Starting base evaluation, run-1 evaluation, four sequential training runs," -ForegroundColor Green
Write-Host "four additional evaluations, aggregation, evidence commit, and Git push." -ForegroundColor Green
Write-Host ""
Write-Host "DO NOT CLOSE THIS WINDOW OR LET WINDOWS SLEEP." -ForegroundColor Yellow
Write-Host ""

& "scripts\run_five_seed_study.ps1" -Repo $Repo

if ($LASTEXITCODE -ne 0) {
    throw "Five-seed controller returned exit code $LASTEXITCODE"
}