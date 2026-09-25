# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Offline replay of the historical five-seed evidence, without loading a model.

PASS means that recorded bytes and independently recomputed measurements agree.
It authenticates neither the author nor the claimed execution. No result from
this module grants promotion or substitutes for a fresh, bound release gate.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import statistics
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Callable

SEEDS = (11, 23, 37, 53, 71)
NAMES = ("base", *(f"seed-{seed:03d}" for seed in SEEDS))
MAX_DOCUMENT_BYTES = 16 * 1024 * 1024
MAX_ADAPTER_BYTES = 1024 * 1024 * 1024
MAX_ROWS = 10000
SCALAR_KEYS = (
    "strict_json_rate", "label_accuracy", "state_accuracy", "joint_accuracy",
    "target_evidence_exact_rate", "evidence_grounding_rate", "refusal_fidelity_rate",
    "median_latency_seconds",
)
COUNT_KEYS = (
    "strict_json", "label_exact", "state_exact", "joint_exact", "target_evidence_exact",
    "predicted_evidence_spans", "grounded_evidence_spans", "refusal_rows",
    "refusal_fidelity", "false_label_on_refusal", "failure_rows",
)
MISSING_BINDINGS = (
    "evaluator_source_sha256", "model_revision", "tokenizer_revision", "chat_template_sha256",
)


class EvidenceError(ValueError):
    """Malformed, missing, or inconsistent evidence with a machine-readable code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise EvidenceError(code, message)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        _require(key not in value, "DUPLICATE_JSON_KEY", f"Duplicate JSON key: {key}")
        value[key] = item
    return value


def _nonfinite(value: str) -> Any:
    raise EvidenceError("NONFINITE_VALUE", f"Non-finite JSON number: {value}")


def _check_finite(value: Any, depth: int = 0) -> None:
    _require(depth < 64, "JSON_DEPTH_LIMIT", "JSON nesting exceeds the audit limit")
    if isinstance(value, float):
        _require(math.isfinite(value), "NONFINITE_VALUE", "Non-finite JSON number")
    elif type(value) is int:
        _require(abs(value) <= (2 ** 63 - 1), "NUMBER_RANGE", "Integer exceeds signed 64-bit audit limit")
    elif isinstance(value, dict):
        for item in value.values():
            _check_finite(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _check_finite(item, depth + 1)


def _loads(text: str) -> Any:
    try:
        value = json.loads(text, object_pairs_hook=_object_pairs, parse_constant=_nonfinite)
        _check_finite(value)
        return value
    except EvidenceError:
        raise
    except (ValueError, RecursionError) as exc:
        raise EvidenceError("MALFORMED_JSON", str(exc)) from exc


def _mapping(value: Any, description: str) -> dict[str, Any]:
    _require(isinstance(value, dict), "SCHEMA_TYPE", f"{description} must be an object")
    return dict(value)


def _number(value: Any, description: str, integer: bool = False) -> None:
    valid = type(value) is int if integer else type(value) in (int, float)
    _require(valid, "SCHEMA_TYPE", f"{description} must be a {'whole ' if integer else ''}number")
    _require(value >= 0 and math.isfinite(value), "VALUE_RANGE",
             f"{description} must be finite and nonnegative")


def _hash(value: Any, description: str) -> None:
    _require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
             "SCHEMA_TYPE", f"{description} must be a lowercase SHA256")


def _same(actual: Any, expected: Any) -> bool:
    """Compare JSON structures while refusing bool-as-int and tolerating float rounding."""
    if type(expected) is bool or type(actual) is bool:
        return type(actual) is type(expected) and actual == expected
    if type(expected) in (int, float) and type(actual) in (int, float):
        if type(expected) is int:
            return type(actual) is int and actual == expected
        return math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12)
    if isinstance(expected, dict) and isinstance(actual, dict):
        return actual.keys() == expected.keys() and all(
            _same(actual[key], item) for key, item in expected.items())
    if isinstance(expected, list) and isinstance(actual, list):
        return len(actual) == len(expected) and all(
            _same(left, right) for left, right in zip(actual, expected))
    return type(actual) is type(expected) and actual == expected


def _family(prompt: str) -> str:
    prefix = " ".join(re.sub(r"[^a-z ]", " ", prompt.lower()).split()[:8])
    return hashlib.sha1(prefix.encode()).hexdigest()[:10]


def _prompt(row: dict[str, Any]) -> str:
    for key in ("input", "text", "prompt"):
        if isinstance(row.get(key), str):
            return str(row[key])
    raise EvidenceError("ROW_BINDING", "Original row has no input/text/prompt string")


def _target(value: Any) -> dict[str, Any]:
    target = _mapping(value, "target")
    _require(set(target) == {"label", "state", "evidence"}, "TARGET_SCHEMA",
             "Target must contain label, state, and evidence")
    _require(target["label"] is None or isinstance(target["label"], str), "TARGET_SCHEMA",
             "Target label must be a string or null")
    _require(isinstance(target["state"], str), "TARGET_SCHEMA", "Target state must be a string")
    _require(isinstance(target["evidence"], list)
             and all(isinstance(item, str) for item in target["evidence"]),
             "TARGET_SCHEMA", "Target evidence must be a list of strings")
    return target


def _seeds(value: Any) -> None:
    _require(isinstance(value, list) and all(type(seed) is int for seed in value)
             and len(value) == len(SEEDS) and set(value) == set(SEEDS), "SEED_SET",
             f"Exactly five distinct seeds are required: {list(SEEDS)}")


def _safe_relative(value: Any) -> Path:
    _require(isinstance(value, str) and bool(value), "UNSAFE_PATH", "Path must be a string")
    portable = value.replace("\\", "/")
    windows, posix = PureWindowsPath(value), PurePosixPath(portable)
    _require(not windows.drive and not windows.root and not posix.is_absolute()
             and ".." not in posix.parts and ":" not in portable,
             "UNSAFE_PATH", "Artifact path must remain relative to the supplied root")
    return Path(*posix.parts)


def _contained(root: Path, relative: Path) -> Path:
    path = (root / relative).resolve()
    _require(path.is_relative_to(root), "UNSAFE_PATH", "Resolved path escapes the supplied root")
    return path


class _Audit:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.inputs: dict[str, dict[str, Any]] = {}
        self.findings: list[dict[str, str]] = []

    def finding(self, code: str, location: str, message: str, severity: str = "error") -> None:
        self.findings.append({"code": code, "severity": severity,
                              "location": location, "message": message})

    def attempt(self, location: str, action: Callable[[], Any]) -> Any:
        try:
            return action()
        except EvidenceError as exc:
            self.finding(exc.code, location, str(exc))
        except (OSError, UnicodeError, csv.Error) as exc:
            self.finding("INPUT_UNREADABLE", location, str(exc))
        return None

    def read(self, relative: str) -> bytes:
        path = _contained(self.root, _safe_relative(relative))
        return self.read_path(path, relative)

    def read_path(self, path: Path, label: str) -> bytes:
        with path.open("rb") as handle:
            data = handle.read(MAX_DOCUMENT_BYTES + 1)
        _require(len(data) <= MAX_DOCUMENT_BYTES, "INPUT_SIZE_LIMIT", "Evidence file exceeds 16 MiB")
        self.inputs[label] = {"path": label, "sha256": _sha(data), "size_bytes": len(data)}
        return data

    def document(self, relative: str) -> Any:
        return _loads(self.read(relative).decode("utf-8-sig"))

    def rows(self, relative: str) -> list[dict[str, Any]]:
        lines = self.read(relative).decode("utf-8-sig").splitlines()
        _require(len(lines) <= MAX_ROWS, "ROW_LIMIT", "JSONL exceeds 10000 lines")
        return [_mapping(_loads(line), f"{relative}:{index}")
                for index, line in enumerate(lines, 1) if line.strip()]

    def schema(self, relative: str, schemas: tuple[str, ...]) -> dict[str, Any]:
        value = _mapping(self.document(relative), relative)
        _require(value.get("schema") in schemas, "SCHEMA_VERSION", f"Expected schema {schemas}")
        return value

    def compare(self, actual: Any, expected: Any, location: str, code: str) -> None:
        if not _same(actual, expected):
            self.finding(code, location, "Stored value does not match independently derived value")


def _frozen(audit: _Audit) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    manifest = audit.schema("frozen/experiment_manifest.json", (
        "szl.frozen-family-split/v1", "szl.five-seed-frozen-split/v1"))
    _seeds(manifest.get("seeds"))
    _require(isinstance(manifest.get("base_model"), str) and bool(manifest["base_model"]),
             "SCHEMA_TYPE", "base_model is required")
    _hash(manifest.get("corpus_sha256"), "corpus_sha256")
    train, held = audit.rows("frozen/train.jsonl"), audit.rows("frozen/held.jsonl")
    for name, records in (("train", train), ("held", held)):
        for key in (f"{name}_rows", f"{name}_families"):
            _number(manifest.get(key), key, integer=True)
        _hash(manifest.get(f"{name}_manifest_sha256"), f"{name}_manifest_sha256")
        audit.compare(manifest[f"{name}_manifest_sha256"],
                      audit.inputs[f"frozen/{name}.jsonl"]["sha256"], name, "FROZEN_HASH_MISMATCH")
        _require(bool(records), "EMPTY_SPLIT", f"{name} split is empty")
        ids: set[str] = set()
        families: set[str] = set()
        for record in records:
            row_id, family = record.get("row_id"), record.get("family")
            _hash(row_id, "row_id")
            _require(row_id not in ids, "DUPLICATE_ROW", f"Duplicate {name} row_id {row_id}")
            _require(isinstance(family, str) and re.fullmatch(r"[a-f0-9]{10}", family) is not None,
                     "SCHEMA_TYPE", "family must be a ten-character hash")
            ids.add(row_id)
            families.add(family)
            original = record.get("row")
            if original is not None:
                row = _mapping(original, "original row")
                audit.compare(row_id, _sha(_canonical(row).encode()), row_id, "ROW_BINDING")
                prompt = _prompt(row)
                if name == "held":
                    audit.compare(record.get("prompt"), prompt, row_id, "ROW_BINDING")
                    audit.compare(record.get("target"), {key: row.get(key, [] if key == "evidence"
                                                                   else None)
                                                       for key in ("label", "state", "evidence")},
                                  row_id, "ROW_BINDING")
            else:
                _require(name == "held", "ROW_BINDING", "Training row source is missing")
                prompt = record.get("prompt")
            _require(isinstance(prompt, str), "SCHEMA_TYPE", "prompt must be a string")
            audit.compare(family, _family(prompt), row_id, "FAMILY_BINDING")
            if name == "held":
                _target(record.get("target"))
        audit.compare(manifest[f"{name}_rows"], len(records), name, "SPLIT_COUNT_MISMATCH")
        audit.compare(manifest[f"{name}_families"], len(families), name, "SPLIT_COUNT_MISMATCH")
    _require(not ({row["row_id"] for row in train} & {row["row_id"] for row in held}),
             "SPLIT_ROW_OVERLAP", "Row IDs overlap across train and held splits")
    _require(not ({row["family"] for row in train} & {row["family"] for row in held}),
             "SPLIT_FAMILY_OVERLAP", "Template families overlap across splits")
    audit.compare(manifest.get("rows"), len(train) + len(held), "manifest.rows", "SPLIT_COUNT_MISMATCH")
    audit.compare(manifest.get("families"), len({row["family"] for row in train + held}),
                  "manifest.families", "SPLIT_COUNT_MISMATCH")
    if any("row" not in row for row in held):
        audit.finding("HELD_SOURCE_ROWS_ABSENT", "frozen/held.jsonl",
                      "Held IDs cannot be rederived from original corpus rows; prompt/target/file "
                      "bindings are checked against this frozen manifest only.", "warning")
    return manifest, train, held


def _parse_prediction(raw: str) -> dict[str, Any] | None:
    # Historical evaluator requires these keys and a list, without repairing output.
    # Reject duplicate keys and non-finite values rather than silently normalizing them.
    try:
        parsed = _loads(raw.strip())
    except EvidenceError:
        return None
    if (not isinstance(parsed, dict) or not {"label", "state", "evidence"}.issubset(parsed)
            or not isinstance(parsed["evidence"], list)):
        return None
    return parsed


def _replay(audit: _Audit, name: str, manifest: dict[str, Any],
            held: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    location = f"evaluation/metrics-{name}.json"
    metrics = audit.schema(location, ("szl.frozen-held-evaluation/v1",))
    audit.compare(metrics.get("name"), name, location, "RUN_IDENTITY")
    audit.compare(metrics.get("base_model"), manifest["base_model"], location, "MODEL_BINDING")
    audit.compare(metrics.get("held_manifest_sha256"), manifest["held_manifest_sha256"],
                  location, "HELD_BINDING")
    decoding = _mapping(metrics.get("decoding"), "decoding")
    repair_key = ("malformed_json_repair" if "malformed_json_repair" in decoding
                  else "repair_malformed_json")
    for key, expected in (("do_sample", False), ("max_new_tokens", 192), (repair_key, False)):
        audit.compare(decoding.get(key), expected, location + ".decoding." + key, "DECODING_MISMATCH")
    for key in ("malformed_json_repair", "repair_malformed_json"):
        if key in decoding:
            audit.compare(decoding[key], False, location + ".decoding." + key, "DECODING_MISMATCH")
    predictions_path = f"evaluation/predictions-{name}.jsonl"
    failures_path = f"evaluation/failures-{name}.jsonl"
    predictions, failures = audit.rows(predictions_path), audit.rows(failures_path)
    for key, path in (("predictions_sha256", predictions_path), ("failures_sha256", failures_path)):
        _hash(metrics.get(key), key)
        audit.compare(metrics[key], audit.inputs[path]["sha256"], location + "." + key,
                      "EVALUATION_HASH_MISMATCH")
    by_id = {row["row_id"]: row for row in held}
    seen: set[str] = set()
    counts = dict.fromkeys(COUNT_KEYS, 0)
    latencies: list[float] = []
    expected_failures: list[dict[str, Any]] = []
    evidence_mismatches: list[str] = []
    for prediction in predictions:
        row_id = prediction.get("row_id")
        _hash(row_id, "prediction.row_id")
        _require(row_id not in seen, "DUPLICATE_PREDICTION", f"Duplicate prediction {row_id}")
        seen.add(row_id)
        _require(row_id in by_id, "PREDICTION_COVERAGE", f"Unknown held row {row_id}")
        gold = by_id[row_id]
        audit.compare(prediction.get("family"), gold["family"], row_id, "PREDICTION_BINDING")
        target_key = "target" if "target" in prediction else "gold"
        audit.compare(prediction.get(target_key), gold["target"], row_id, "PREDICTION_BINDING")
        if "gold" in prediction and "target" in prediction:
            audit.compare(prediction["gold"], gold["target"], row_id, "PREDICTION_BINDING")
        raw = prediction.get("raw_output")
        _require(isinstance(raw, str), "SCHEMA_TYPE", "raw_output must be a string")
        latency = prediction.get("latency_seconds")
        _number(latency, "latency_seconds")
        latencies.append(latency)
        parsed = _parse_prediction(raw)
        label = parsed.get("label") if parsed is not None else None
        state = parsed.get("state") if parsed is not None else None
        spans = parsed["evidence"] if parsed is not None else []
        target = gold["target"]
        flags = [isinstance(span, str) and span in gold["prompt"] for span in spans]
        label_ok, state_ok = label == target["label"], state == target["state"]
        joint_ok, evidence_ok = label_ok and state_ok, spans == target["evidence"]
        derived = {"parsed": parsed, "label_exact": label_ok, "state_exact": state_ok,
                   "joint_exact": joint_ok, "target_evidence_exact": evidence_ok,
                   "grounded_evidence_flags": flags}
        for key, value in derived.items():
            audit.compare(prediction.get(key), value, f"{name}:{row_id}.{key}", "PREDICTION_REPLAY_MISMATCH")
        counts["strict_json"] += int(parsed is not None)
        counts["label_exact"] += int(label_ok)
        counts["state_exact"] += int(state_ok)
        counts["joint_exact"] += int(joint_ok)
        counts["target_evidence_exact"] += int(evidence_ok)
        counts["predicted_evidence_spans"] += len(flags)
        counts["grounded_evidence_spans"] += sum(flags)
        if target["state"] == "REVIEW":
            counts["refusal_rows"] += 1
            counts["refusal_fidelity"] += int(state == "REVIEW")
            counts["false_label_on_refusal"] += int(state != "REVIEW")
        if not evidence_ok:
            evidence_mismatches.append(row_id)
        if parsed is None or not joint_ok or not all(flags):
            expected_failures.append(prediction)
    _require(seen == set(by_id), "PREDICTION_COVERAGE", "Predictions do not cover every held row exactly once")
    audit.compare(failures, expected_failures, failures_path, "FAILURE_SET_MISMATCH")
    counts["failure_rows"] = len(expected_failures)
    n = len(held)
    values: dict[str, Any] = {**counts, "held_rows": n}
    for rate, numerator, denominator in (
        ("strict_json_rate", "strict_json", n), ("label_accuracy", "label_exact", n),
        ("state_accuracy", "state_exact", n), ("joint_accuracy", "joint_exact", n),
        ("target_evidence_exact_rate", "target_evidence_exact", n),
        ("evidence_grounding_rate", "grounded_evidence_spans", counts["predicted_evidence_spans"]),
        ("refusal_fidelity_rate", "refusal_fidelity", counts["refusal_rows"]),
    ):
        values[rate] = counts[numerator] / denominator if denominator else None
    values["median_latency_seconds"] = statistics.median(latencies)
    for key in COUNT_KEYS:
        _number(metrics.get(key), key, integer=True)
    for key, expected in values.items():
        stored_key = "rows" if key == "held_rows" and "held_rows" not in metrics else key
        audit.compare(metrics.get(stored_key), expected, f"{location}.{stored_key}", "METRIC_REPLAY_MISMATCH")
    if "rows" in metrics and "held_rows" in metrics:
        audit.compare(metrics["rows"], n, location + ".rows", "METRIC_REPLAY_MISMATCH")
    values["failure_row_ids"] = [row["row_id"] for row in expected_failures]
    values["target_evidence_mismatch_row_ids"] = evidence_mismatches
    return metrics, values


def _aggregate(audit: _Audit, manifest: dict[str, Any], metrics: dict[str, dict[str, Any]],
               runs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    aggregate = audit.schema("evaluation/aggregate_metrics.json", ("szl.five-seed-aggregate/v1",))
    _seeds(aggregate.get("seeds"))
    audit.compare(aggregate.get("base_model"), manifest["base_model"], "aggregate", "MODEL_BINDING")
    audit.compare(aggregate.get("held_rows"), manifest["held_rows"], "aggregate", "HELD_BINDING")
    targets = aggregate.get("targets")
    _require(isinstance(targets, list) and len(targets) == len(NAMES), "RUN_SET",
             "Aggregate must contain the base and exactly five seed targets")
    names = []
    for target in targets:
        target = _mapping(target, "aggregate target")
        name = target.get("name")
        _require(isinstance(name, str) and name in NAMES and name not in names,
                 "RUN_SET", "Aggregate contains unknown or duplicate targets")
        names.append(name)
        if name in metrics:
            audit.compare(target, metrics[name], f"aggregate.targets.{name}", "AGGREGATE_TARGET_MISMATCH")
    summary: dict[str, Any] = {}
    if set(runs) == set(NAMES):
        for key in SCALAR_KEYS:
            values = [runs[name][key] for name in NAMES[1:] if runs[name][key] is not None]
            summary[key] = {"n": len(values), "mean": statistics.fmean(values) if values else None,
                            "sample_std": statistics.stdev(values) if len(values) > 1 else None,
                            "min": min(values) if values else None, "max": max(values) if values else None}
        audit.compare(aggregate.get("five_seed_summary"), summary,
                      "aggregate.five_seed_summary", "AGGREGATE_SUMMARY_MISMATCH")
    return {"stored": aggregate, "summary": summary}


def _training(audit: _Audit, manifest: dict[str, Any]) -> tuple[dict[int, dict[str, Any]],
                                                             list[dict[str, Any]]]:
    index = audit.document("adapter-index.json")
    _require(isinstance(index, list), "SCHEMA_TYPE", "adapter-index must be a list")
    entries = [_mapping(item, "adapter index entry") for item in index]
    _seeds([item.get("seed") for item in entries])
    receipts: dict[int, dict[str, Any]] = {}
    reference: dict[str, Any] | None = None
    for entry in entries:
        seed = entry["seed"]
        _hash(entry.get("adapter_sha256"), "adapter_sha256")
        relative = _safe_relative(entry.get("local_path"))
        path = f"training/training_receipt-seed-{seed:03d}.json"
        receipt = audit.schema(path, ("szl.training/v1",))
        _require(receipt.get("state") == "MEASURED" and receipt.get("status") == "MEASURED",
                 "TRAINING_STATE_MISMATCH", "Training state and status must both be MEASURED")
        # Corroborate the recorded binding claim. This does not inspect tensor values.
        for key in ("lora_b_total", "lora_b_nonzero"):
            _number(receipt.get(key), key, integer=True)
        _require(receipt["lora_b_total"] > 0
                 and receipt["lora_b_nonzero"] == receipt["lora_b_total"],
                 "TRAINING_BINDING_FAILED", "Recorded LoRA B counts do not support binding PASS")
        hyper = _mapping(receipt.get("hyperparameters"), "hyperparameters")
        for key in ("seed", "r", "alpha", "epochs", "batch", "grad_accum"):
            _number(hyper.get(key), key, integer=True)
            _require(hyper[key] > 0, "VALUE_RANGE", f"{key} must be positive")
        for key in ("dropout", "lr"):
            _number(hyper.get(key), key)
        _require(hyper["lr"] > 0 and hyper["dropout"] < 1, "VALUE_RANGE", "Invalid learning rate/dropout")
        for key in ("dtype", "quantization"):
            _require(isinstance(hyper.get(key), str) and bool(hyper[key]), "SCHEMA_TYPE", f"{key} required")
        audit.compare(hyper["seed"], seed, path, "TRAINING_SEED_MISMATCH")
        comparable = {key: value for key, value in hyper.items() if key != "seed"}
        if reference is None:
            reference = comparable
        audit.compare(comparable, reference, path, "TRAINING_HPARAM_MISMATCH")
        audit.compare(receipt.get("base_model"), manifest["base_model"], path, "MODEL_BINDING")
        audit.compare(_safe_relative(receipt.get("adapter_path")).as_posix(), relative.as_posix(),
                      path, "ADAPTER_PATH_MISMATCH")
        audit.compare(_safe_relative(receipt.get("corpus")).as_posix(),
                      _safe_relative(manifest.get("corpus")).as_posix(), path, "CORPUS_BINDING")
        for key in ("rows", "families"):
            audit.compare(receipt.get(key), manifest[key], path, "TRAINING_SPLIT_MISMATCH")
        split = _mapping(receipt.get("split"), "training split")
        for key in ("train_rows", "held_rows"):
            audit.compare(split.get(key), manifest[key], path, "TRAINING_SPLIT_MISMATCH")
        for key in ("seconds", "final_training_loss"):
            _number(receipt.get(key), key)
            _number(entry.get(key), key)
            audit.compare(entry[key], receipt[key], path, "ADAPTER_INDEX_MISMATCH")
        audit.compare(entry.get("binding_check"), receipt.get("binding_check"), path, "ADAPTER_INDEX_MISMATCH")
        _require(receipt.get("binding_check") == "PASS", "TRAINING_BINDING_FAILED", "Training binding was not PASS")
        receipts[seed] = receipt
    return receipts, entries


def _adapters(audit: _Audit, artifact_root: Path, entries: list[dict[str, Any]],
              receipts: dict[int, dict[str, Any]]) -> list[int]:
    verified: list[int] = []
    root = artifact_root.resolve()
    for entry in entries:
        def inspect() -> int:
            directory = _contained(root, _safe_relative(entry["local_path"]))
            weights = _contained(root, directory / "adapter_model.safetensors")
            size = weights.stat().st_size
            _require(size <= MAX_ADAPTER_BYTES, "INPUT_SIZE_LIMIT", "Adapter exceeds 1 GiB audit limit")
            digest, consumed = hashlib.sha256(), 0
            with weights.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    consumed += len(block)
                    _require(consumed <= MAX_ADAPTER_BYTES, "INPUT_SIZE_LIMIT", "Adapter grew beyond limit")
                    digest.update(block)
            label = "artifact/" + weights.relative_to(root).as_posix()
            audit.inputs[label] = {"path": label, "sha256": digest.hexdigest(), "size_bytes": consumed}
            _require(digest.hexdigest() == entry["adapter_sha256"], "ADAPTER_HASH_MISMATCH",
                     "Local adapter bytes differ from the indexed SHA256")
            config_path = _contained(root, directory / "adapter_config.json")
            config_label = "artifact/" + config_path.relative_to(root).as_posix()
            config = _mapping(_loads(audit.read_path(config_path, config_label).decode("utf-8-sig")), "adapter config")
            receipt = receipts[entry["seed"]]
            hyper = receipt["hyperparameters"]
            for key, expected in (("base_model_name_or_path", receipt["base_model"]),
                                  ("r", hyper["r"]), ("lora_alpha", hyper["alpha"]),
                                  ("lora_dropout", hyper["dropout"]), ("peft_type", "LORA")):
                _require(_same(config.get(key), expected), "ADAPTER_CONFIG_MISMATCH",
                         f"Adapter config {key} differs from training receipt")
            return int(entry["seed"])
        seed = audit.attempt(f"adapter:{entry['seed']}", inspect)
        if seed is not None:
            verified.append(seed)
    return verified


def _csv(audit: _Audit, metrics: dict[str, dict[str, Any]]) -> None:
    text = audit.read("evaluation/metrics.csv").decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    fields = ["name", *(key for key in SCALAR_KEYS if key != "target_evidence_exact_rate"),
              "false_label_on_refusal", "failure_rows"]
    _require(reader.fieldnames is not None and len(reader.fieldnames) == len(set(reader.fieldnames))
             and set(fields).issubset(reader.fieldnames), "CSV_SCHEMA", "CSV required columns missing or duplicated")
    seen: set[str] = set()
    rows = list(reader)
    _require(len(rows) == len(NAMES), "RUN_SET", "CSV must contain six runs")
    for row in rows:
        name = row.get("name")
        _require(isinstance(name, str) and name in NAMES and name not in seen, "RUN_SET", "CSV duplicate or unknown run")
        seen.add(name)
        if name not in metrics:
            continue
        for key, value in row.items():
            _require(key in metrics[name], "CSV_SCHEMA", "Unknown CSV metric column")
            expected = metrics[name][key]
            if key == "name":
                actual: Any = value
            elif value == "":
                actual = None
            else:
                try:
                    actual = int(value) if type(expected) is int else float(value)
                except (TypeError, ValueError) as exc:
                    raise EvidenceError("CSV_SCHEMA", f"Invalid CSV number in {key}") from exc
                _number(actual, key)
            audit.compare(actual, expected, f"metrics.csv:{name}.{key}", "CSV_METRIC_MISMATCH")


def _release(audit: _Audit, path: Path) -> dict[str, Any]:
    value = _mapping(_loads(audit.read_path(path.resolve(), "release_gate").decode("utf-8-sig")), "release gate")
    verdict = value.get("release_verdict")
    _require(verdict in ("BLOCKED", "PROMOTABLE"), "RELEASE_GATE_SCHEMA",
             "Expected release_verdict BLOCKED or PROMOTABLE; an unrelated status is not a gate")
    stages = _mapping(value.get("stages"), "release stages")
    _require({"in_domain", "red_team", "leakage"}.issubset(stages), "RELEASE_GATE_SCHEMA",
             "Release gate must include in_domain, red_team, and leakage stages")
    for name, stage in stages.items():
        stage = _mapping(stage, name)
        _require(type(stage.get("stage_passed")) is bool and type(stage.get("exit")) is int
                 and isinstance(stage.get("breaches"), dict), "RELEASE_GATE_SCHEMA", "Malformed release stage")
        if stage["stage_passed"]:
            _require(stage["exit"] == 0 and not stage["breaches"], "RELEASE_GATE_CONTRADICTION",
                     "A passing stage has a failing exit or breaches")
    derived = "PROMOTABLE" if all(stage["stage_passed"] for stage in stages.values()) else "BLOCKED"
    _require(verdict == derived, "RELEASE_GATE_CONTRADICTION", "Release verdict contradicts its stages")
    audit.finding("RELEASE_GATE_NOT_BOUND", "release_gate", "Receipt is reported, but this auditor "
                  "cannot establish freshness or bind its model/corpus to all five study adapters.", "warning")
    return {"provided": True, "status": "REPORTED_UNBOUND", "reported": verdict,
            "stages": {key: item["stage_passed"] for key, item in stages.items()}}


def audit_study(evidence_dir: Path, artifact_root: Path | None = None,
                release_gate: Path | None = None) -> dict[str, Any]:
    """Return a bounded, deterministic audit; never write, train, infer, or use network.

    ``artifact_root`` is an explicit root for adapter-index relative paths. When
    omitted, adapter hashes remain claims and local adapter verification is not
    performed. A release receipt is reported separately and never grants promotion.
    Malformed evidence returns FAIL with named findings, rather than a partial PASS.
    """
    audit = _Audit(Path(evidence_dir))
    runs: dict[str, dict[str, Any]] = {}
    metrics: dict[str, dict[str, Any]] = {}
    summary: dict[str, Any] = {}
    missing: dict[str, list[str]] = {}
    manifest: dict[str, Any] = {}
    training: dict[int, dict[str, Any]] = {}
    entries: list[dict[str, Any]] = []
    train_count = held_count = 0
    result = audit.attempt("frozen", lambda: _frozen(audit))
    if result is not None:
        manifest, train, held = result
        train_count, held_count = len(train), len(held)
        for pattern, expected in (
            ("evaluation/metrics-*.json", {f"metrics-{name}.json" for name in NAMES}),
            ("evaluation/predictions-*.jsonl", {f"predictions-{name}.jsonl" for name in NAMES}),
            ("evaluation/failures-*.jsonl", {f"failures-{name}.jsonl" for name in NAMES}),
            ("training/training_receipt-*.json", {f"training_receipt-seed-{seed:03d}.json" for seed in SEEDS}),
        ):
            audit.compare(sorted(path.name for path in audit.root.glob(pattern)), sorted(expected),
                          pattern, "RUN_FILE_SET")
        for name in NAMES:
            replay = audit.attempt(name, lambda name=name: _replay(audit, name, manifest, held))
            if replay is not None:
                metrics[name], runs[name] = replay
                required = (*MISSING_BINDINGS, *(("adapter_sha256",) if name != "base" else ()))
                missing[name] = [key for key in required if not metrics[name].get(key)]
        aggregate = audit.attempt("aggregate", lambda: _aggregate(audit, manifest, metrics, runs))
        if aggregate is not None:
            summary = aggregate["summary"]
        audit.attempt("metrics.csv", lambda: _csv(audit, metrics))
        training_result = audit.attempt("training", lambda: _training(audit, manifest))
        if training_result is not None:
            training, entries = training_result
    artifacts: dict[str, Any] = {"status": "NOT_REQUESTED", "verified_seeds": []}
    if artifact_root is not None:
        verified = _adapters(audit, Path(artifact_root), entries, training) if entries else []
        artifacts = {"status": "VERIFIED" if set(verified) == set(SEEDS) else "FAILED",
                     "verified_seeds": verified}
        if not entries:
            audit.finding("ARTIFACT_VERIFICATION_UNAVAILABLE", "adapter-index.json",
                          "Adapter verification requires valid training/index evidence")
    artifacts["scope"] = "BYTE_HASH_AND_CONFIG_ONLY"
    artifacts["tensor_values_verified"] = False
    gate = {"provided": False, "status": "NOT_SUPPLIED", "reported": None}
    if release_gate is not None:
        gate = audit.attempt("release_gate", lambda: _release(audit, Path(release_gate))) or {
            "provided": True, "status": "INVALID", "reported": None}
    audit.finding("HISTORICAL_REPLAY_ONLY", "provenance", "Recorded-output replay is not a model "
                  "rerun. Hashes identify bytes, not authenticated execution or authorship.", "warning")
    if any(missing.values()):
        audit.finding("EVALUATION_PROVENANCE_INCOMPLETE", "evaluation", "Historical evaluations "
                      "lack evaluator/model/tokenizer/template or adapter identity bindings.", "warning")
    blocked = (manifest.get("promotion_status") == "NOT_PROMOTABLE"
               or manifest.get("release_status") == "BLOCKED" or gate.get("reported") == "BLOCKED"
               or any(receipt.get("leakage_verdict_at_training_time") == "REFUSED"
                      or receipt.get("promotion_status") == "NOT_PROMOTABLE" for receipt in training.values()))
    inputs = sorted(audit.inputs.values(), key=lambda item: item["path"])
    return {
        "schema": "szl.study-evidence-audit/v1",
        "integrity_status": "FAIL" if any(item["severity"] == "error" for item in audit.findings) else "PASS",
        "promotion_status": "NOT_PROMOTABLE" if blocked else "NOT_ESTABLISHED",
        "findings": audit.findings,
        "replay": {"runs": runs, "five_seed_summary": summary,
                   "held_rows": held_count, "train_rows": train_count},
        "release_gate": gate,
        "provenance": {"status": "HISTORICAL_REPLAY_ONLY", "missing_bindings": missing,
                       "authenticated_execution": False, "model_rerun": False},
        "artifact_verification": artifacts,
        "inputs": inputs,
        "bundle_sha256": _sha(_canonical(inputs).encode()),
        "scope": "Frozen splits, predictions, failure sets, metrics, CSV, aggregate, training "
                 "receipts and adapter index; optional local adapters and release receipt. "
                 "Publication and environment receipts are not independently verified.",
    }
