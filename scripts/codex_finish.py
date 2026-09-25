"""Replay the saved study and run bounded inference without implicit publication.

The original handoff described guessed flags and unverified receipt discovery.
This entry point uses the actual study layout and never trains or publishes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT / "src"))
sys.path.insert(0, str(SOURCE_ROOT / "scripts"))

from szl_triage.study_evidence import audit_study  # noqa: E402 - checkout-local CLI

SECRET = re.compile(r"hf_[A-Za-z0-9]{20,}|gh[opsu]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}")


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def emit(value: object) -> None:
    print(SECRET.sub("[REDACTED]", json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False)))


def save_new(path: Path, value: object) -> None:
    content = json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + "\n"
    if SECRET.search(content):
        raise ValueError("Refusing token-like content in output")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def source_identity() -> dict:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", "HEAD"], cwd=SOURCE_ROOT,
        capture_output=True, text=True, check=False,
    )
    files = ["scripts/codex_finish.py", "scripts/train_eval_publish.py", "scripts/triage_text.py",
             "src/szl_triage/study_evidence.py"]
    return {"head": result.stdout.strip() if result.returncode == 0 else None,
            "files_sha256": {name: digest(SOURCE_ROOT / name) for name in files}}


def audit(args: argparse.Namespace) -> dict:
    report = audit_study(args.evidence, artifact_root=args.artifact_root, release_gate=args.release_gate)
    report["auditor_source"] = source_identity()
    return report


def smoke(args: argparse.Namespace) -> dict:
    """New receipt, historical adapter, bounded examples; no old evidence writes."""
    if args.artifact_root is None:
        raise ValueError("smoke requires --artifact-root containing the saved adapters")
    if args.output is None:
        raise ValueError("smoke requires --output pointing to a new receipt file")
    if args.output.exists():
        raise FileExistsError("Smoke output already exists; choose a new receipt path")
    before = audit(args)
    if before["integrity_status"] != "PASS":
        raise ValueError("Study integrity failed; use audit to inspect the findings before smoke")
    source_before = source_identity()
    entries = json.loads((args.evidence / "adapter-index.json").read_text(encoding="utf-8-sig"))
    entry = next(item for item in entries if item["seed"] == args.seed)
    relative = Path(entry["local_path"].replace("\\", "/"))
    adapter = args.artifact_root / relative
    adapter = adapter.resolve()
    adapter.relative_to(args.artifact_root.resolve())
    weights_before = digest(adapter / "adapter_model.safetensors")
    if weights_before != entry["adapter_sha256"]:
        raise ValueError("Selected adapter differs from the indexed weight digest")
    config_before = digest(adapter / "adapter_config.json")
    records = read_jsonl(args.evidence / "frozen" / "held.jsonl")
    # Include refusal and ordinary rows when both are present, then fill in order.
    selected = []
    for review in (False, True):
        row = next((r for r in records if (r["target"].get("state") == "REVIEW") == review), None)
        if row is not None and len(selected) < args.limit:
            selected.append(row)
    selected += [r for r in records if r not in selected][:args.limit - len(selected)]
    os.environ["SZL_ALLOW_HUB_PUSH"] = "0"
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    # Existing cached model only. Missing dependencies/cache are errors, never auto-installed.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    if args.eager:
        os.environ["UNSLOTH_COMPILE_DISABLE"] = "1"
        os.environ["TORCH_COMPILE_DISABLE"] = "1"
    from train_eval_publish import load_model, generate, strict_json
    from triage_text import template_contract
    import importlib.metadata
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable for the requested GPU smoke")
    capability = torch.cuda.get_device_capability()
    architecture = f"sm_{capability[0]}{capability[1]}"
    if architecture not in torch.cuda.get_arch_list():
        raise RuntimeError(f"CUDA wheel lacks required {architecture}")
    model, tokenizer = load_model(str(adapter))
    contract = template_contract(tokenizer)
    results = []
    for record in selected:
        raw, latency = generate(model, tokenizer, record["prompt"])
        parsed = strict_json(raw)
        results.append({"row_id": record["row_id"], "target": record["target"],
                        "raw_output": raw, "parsed": parsed, "latency_seconds": latency,
                        "joint_exact": parsed is not None and all(
                            parsed.get(k) == record["target"].get(k) for k in ("label", "state"))})
    after = audit(args)
    if (after["integrity_status"] != "PASS"
            or before["bundle_sha256"] != after["bundle_sha256"]
            or source_identity() != source_before
            or digest(adapter / "adapter_model.safetensors") != weights_before
            or digest(adapter / "adapter_config.json") != config_before):
        raise RuntimeError("Study or adapter changed during smoke; no completion receipt written")
    return {"schema": "szl.text-inference-smoke/v1", "state": "EXECUTED",
            "scope": "BOUNDED_RUNTIME_SMOKE_ON_HISTORICAL_SYNTHETIC_ROWS",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(), "seed": args.seed,
            "source": source_before, "study_bundle_sha256": before["bundle_sha256"],
            "adapter_sha256": weights_before, "adapter_config_sha256": config_before,
            "template_contract": contract, "decoding": {"do_sample": False, "max_new_tokens": 192},
            "compilation": {"eager_requested": args.eager,
                            "unsloth_compile_disable": os.environ.get("UNSLOTH_COMPILE_DISABLE", "0"),
                            "torch_compile_disable": os.environ.get("TORCH_COMPILE_DISABLE", "0")},
            "environment": {"torch": torch.__version__, "architecture": architecture,
                            "device": torch.cuda.get_device_name(0),
                            "transformers": importlib.metadata.version("transformers"),
                            "unsloth": importlib.metadata.version("unsloth")},
            "base_revision_observed": getattr(model.config, "_commit_hash", None),
            "rows": len(results), "results": results,
            "all_joint_exact": all(r["joint_exact"] for r in results),
            "promotion_status": before["promotion_status"], "release_gate": before["release_gate"],
            "limitations": ["Not a new five-seed evaluation or a generalization benchmark.",
                            "Historical training template and base revision were not sealed at training time."]}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("stage", nargs="?", choices=["audit", "smoke", "publish-plan"], default="audit")
    result.add_argument("--evidence", type=Path, default=SOURCE_ROOT / "evidence" / "five-seed-study")
    result.add_argument("--artifact-root", type=Path, help="Optional existing run checkout; read-only")
    result.add_argument("--release-gate", type=Path, default=SOURCE_ROOT / "out" / "release_gate.json")
    result.add_argument("--output", type=Path, help="New JSON output; existing files are never overwritten")
    result.add_argument("--seed", type=int, choices=[11, 23, 37, 53, 71], default=11)
    result.add_argument("--limit", type=int, choices=range(1, 6), default=3, help="Smoke rows (1 to 5)")
    result.add_argument("--eager", action="store_true", help="Disable model compilation for a functional smoke; mode is recorded")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        report = smoke(args) if args.stage == "smoke" else audit(args)
        if args.stage == "publish-plan":
            report = {"schema": "szl.study-publication-plan/v1", "mode": "READ_ONLY",
                      "bundle_sha256": report["bundle_sha256"],
                      "integrity_status": report["integrity_status"],
                      "promotion_status": report["promotion_status"],
                      "release_gate": report["release_gate"], "operations": [],
                      "reason": "Review a new research evidence bundle through a PR. No Hub, profile, or social writes are implemented."}
        if args.output is not None:
            save_new(args.output, report)
        emit(report)
        return 0 if report.get("integrity_status", "PASS") == "PASS" else 2
    except Exception as exc:
        failure = {"state": "FAILED", "error_type": type(exc).__name__,
                   "error": SECRET.sub("[REDACTED]", str(exc))}
        if args.output is not None and not args.output.exists():
            try:
                save_new(args.output, failure)
            except (OSError, ValueError):
                pass  # Report the original failure; never overwrite a raced output.
        emit(failure)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
