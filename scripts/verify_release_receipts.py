# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Verify recorded release evidence without rerunning models or altering receipts.

The v2 contract requires exactly three stages. The historical unversioned
projection remains readable; missing bindings remain errors. A valid negative
receipt can pass integrity verification while promotion remains blocked.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

STAGES = {"in_domain", "red_team", "leakage"}
MODEL_CORPORA = {
    "in_domain": "output/triage_distill_split_v0.4.0.jsonl",
    "red_team": "policies/redteam_probes.verified.jsonl",
}
LIMIT = 16 * 1024 * 1024


class InvalidEvidence(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise InvalidEvidence(code, message)


def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        require(key not in value, "DUPLICATE_KEY", f"Duplicate JSON key {key}")
        value[key] = item
    return value


def finite(value: Any, depth: int = 0) -> None:
    require(depth < 64, "JSON_DEPTH", "JSON exceeds nesting limit")
    if isinstance(value, float):
        require(math.isfinite(value), "NONFINITE_NUMBER", "Non-finite JSON number")
    elif type(value) is int:
        require(abs(value) <= 2 ** 63 - 1, "NUMBER_RANGE", "Integer exceeds audit limit")
    elif isinstance(value, dict):
        for item in value.values():
            finite(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            finite(item, depth + 1)


def decode(data: bytes) -> Any:
    try:
        value = json.loads(data.decode("utf-8-sig"), object_pairs_hook=object_pairs)
        finite(value)
        return value
    except InvalidEvidence:
        raise
    except (ValueError, RecursionError) as exc:
        raise InvalidEvidence("MALFORMED_JSON", str(exc)) from exc


def object_value(value: Any, label: str) -> dict[str, Any]:
    require(isinstance(value, dict), "FIELD_TYPE", f"{label} must be an object")
    return value


def integer(value: Any, label: str, minimum: int = 0) -> int:
    require(type(value) is int and value >= minimum, "FIELD_TYPE",
            f"{label} must be an integer >= {minimum}; booleans are not counts")
    return value


def digest(value: Any, label: str) -> str:
    require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
            "MISSING_DIGEST", f"{label} must contain an exact SHA256")
    return value


def relative(value: Any) -> str:
    require(isinstance(value, str) and bool(value.strip()), "INVALID_PATH",
            "Nonempty relative path required")
    normalized = value.replace("\\", "/")
    windows, posix = PureWindowsPath(value), PurePosixPath(normalized)
    require(not windows.drive and not windows.root and not posix.is_absolute()
            and ".." not in posix.parts and ":" not in normalized and bool(posix.parts),
            "PATH_ESCAPE", "Evidence path must remain inside the repository")
    return posix.as_posix()


class Verifier:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.findings: list[dict[str, str]] = []
        self.inputs: dict[str, dict[str, Any]] = {}
        self.candidates: dict[str, Path] = {}

    def finding(self, code: str, stage: str, message: str) -> None:
        self.findings.append({"code": code, "stage": stage, "message": message})

    def path(self, name: str) -> Path:
        path = (self.root / relative(name)).resolve()
        require(path.is_relative_to(self.root), "PATH_ESCAPE",
                "Resolved evidence path escapes repository")
        return path

    def read(self, name: str) -> bytes:
        path = self.path(name)
        require(path.is_file(), "MISSING_FILE", f"Evidence is not a regular file: {name}")
        with path.open("rb") as handle:
            data = handle.read(LIMIT + 1)
        require(len(data) <= LIMIT, "SIZE_LIMIT", "Evidence exceeds 16 MiB audit limit")
        self.inputs[name] = {"path": name, "sha256": hashlib.sha256(data).hexdigest(),
                             "size_bytes": len(data)}
        return data

    def document(self, name: str) -> dict[str, Any]:
        return object_value(decode(self.read(name)), name)

    def corpus(self, name: str, expected: Any) -> list[dict[str, Any]]:
        expected = digest(expected, "corpus_sha256")
        data = self.read(name)
        require(hashlib.sha256(data).hexdigest() == expected, "CORPUS_HASH_MISMATCH",
                f"Corpus bytes differ from recorded SHA256: {name}")
        records = [object_value(decode(line), "corpus row")
                   for line in data.splitlines() if line.strip()]
        require(bool(records), "EMPTY_CORPUS", "Corpus cannot be empty")
        return records

    def common(self, name: str, stage: dict[str, Any]) -> None:
        integer(stage.get("exit"), "exit")
        require(type(stage.get("stage_passed")) is bool, "FIELD_TYPE",
                "stage_passed must be boolean")
        object_value(stage.get("breaches"), "breaches")
        verdicts = ("CLEAN", "REFUSED") if name == "leakage" else ("PROMOTABLE", "BLOCKED")
        require(stage.get("verdict") in verdicts, "STAGE_VERDICT",
                f"{name} verdict must be one of {verdicts}")
        positive = "CLEAN" if name == "leakage" else "PROMOTABLE"
        derived = stage["exit"] == 0 and stage["verdict"] == positive and not stage["breaches"]
        require(stage["stage_passed"] == derived, "STAGE_CONTRADICTION",
                "stage_passed contradicts exit, verdict, or breaches")

    def model(self, name: str, stage: dict[str, Any]) -> None:
        self.common(name, stage)
        self.candidates[name] = self.path(relative(stage.get("adapter")))
        corpus = relative(stage.get("data_path"))
        require(corpus == MODEL_CORPORA[name], "STAGE_CORPUS_MISMATCH",
                f"{name} requires {MODEL_CORPORA[name]}, but the receipt names {corpus}")
        rows = integer(stage.get("rows"), "rows", 1)
        for key in ("label_ok", "state_ok"):
            require(integer(stage.get(key), key) <= rows, "COUNT_RANGE", f"{key} exceeds rows")
        for key, value in stage["breaches"].items():
            require(key in {"false_label_on_refusal", "ungrounded_spans", "malformed"},
                    "UNKNOWN_BREACH", f"Unknown model breach {key}")
            integer(value, f"breaches.{key}", 1)
        records = self.corpus(corpus, stage.get("corpus_sha256"))
        held_count = sum(row.get("split") != "train" for row in records)
        require(rows == held_count, "ROW_COUNT_MISMATCH",
                f"Recorded rows {rows} do not match {held_count} non-training corpus rows")

    def leakage_metrics(self, receipt: dict[str, Any]) -> None:
        rows = integer(receipt.get("rows"), "leakage.rows", 1)
        families = integer(receipt.get("template_families"), "template_families", 1)
        largest = integer(receipt.get("largest_family"), "largest_family", 1)
        exact = integer(receipt.get("exact_duplicates_across_split"), "exact_duplicates_across_split")
        shared = integer(receipt.get("shared_template_families"), "shared_template_families")
        require(families <= rows and largest <= rows - families + 1
                and largest * families >= rows and exact <= rows // 2
                and shared <= min(families, rows // 2),
                "COUNT_RANGE", "Leakage counts contradict the declared corpus/split size")
        similarity = receipt.get("max_char5gram_jaccard")
        require(type(similarity) in (int, float) and 0 <= similarity <= 1,
                "FIELD_TYPE", "max_char5gram_jaccard must be a finite number in [0, 1]")
        reasons = receipt.get("reasons")
        require(isinstance(reasons, list)
                and all(isinstance(reason, str) and bool(reason.strip()) for reason in reasons),
                "FIELD_TYPE", "Leakage reasons must be a list of nonempty strings")
        if receipt["verdict"] == "CLEAN":
            # Preserve the actual v1 producer rule. Its rounded similarity cannot
            # prove unrounded cleanliness, but a value above .70 contradicts CLEAN.
            require(exact == 0 and shared == 0 and similarity <= 0.70
                    and families >= max(8, rows // 20) and not reasons,
                    "LEAKAGE_METRIC_CONTRADICTION",
                    "CLEAN contradicts duplicate/family/Jaccard/reason evidence under leakage v1")
        else:
            require(bool(reasons), "LEAKAGE_METRIC_CONTRADICTION",
                    "A REFUSED leakage receipt must retain its reasons")

    def leakage(self, stage: dict[str, Any], versioned: bool) -> None:
        self.common("leakage", stage)
        # The old producer used a fixed sidecar. Reading it exposes inconsistency;
        # it never creates the missing historical digest or commit binding.
        name = relative(stage.get("receipt_path") if versioned
                        else stage.get("receipt_path", "out/leakage_gate.json"))
        receipt = self.document(name)
        expected_digest = stage.get("receipt_sha256")
        if expected_digest is None:
            self.finding("LEAKAGE_RECEIPT_UNBOUND", "leakage",
                         "Summary has no receipt_sha256; today's sidecar cannot supply that binding")
        else:
            require(digest(expected_digest, "receipt_sha256") == self.inputs[name]["sha256"],
                    "LEAKAGE_RECEIPT_HASH_MISMATCH", "Leakage receipt differs from declared digest")
        require(receipt.get("schema") == "szl.leakage-gate/v1", "LEAKAGE_SCHEMA",
                "Unsupported leakage schema")
        declared_commit = stage.get("commit")
        if declared_commit is None:
            self.finding("LEAKAGE_COMMIT_UNBOUND", "leakage",
                         "Summary has no explicit leakage commit binding")
            observed_commit = stage["breaches"].get("commit")
            if observed_commit is not None and observed_commit != receipt.get("commit"):
                self.finding("LEAKAGE_COMMIT_MISMATCH", "leakage",
                             "Commit in historical breaches differs from the available sidecar")
        else:
            require(isinstance(declared_commit, str)
                    and re.fullmatch(r"[0-9a-f]{7,40}", declared_commit) is not None,
                    "FIELD_TYPE", "Leakage commit must be a Git object ID")
            require(declared_commit == receipt.get("commit"), "LEAKAGE_COMMIT_MISMATCH",
                    "Summary and leakage receipt commits differ")
        require(receipt.get("status") == "MEASURED", "LEAKAGE_STATE",
                "Leakage status must be MEASURED")
        require(stage["verdict"] == receipt.get("verdict"), "LEAKAGE_VERDICT_MISMATCH",
                "Summary and leakage receipt verdicts differ")
        semantic = receipt.get("semantic_pass")
        require(semantic in ("PASS", "FAIL", "UNAVAILABLE"), "LEAKAGE_SCHEMA",
                "Explicit semantic result required")
        if stage["stage_passed"]:
            require(semantic == "PASS", "LEAKAGE_SEMANTIC_NOT_PASS",
                    "Unavailable or failing semantic evidence cannot pass")
        self.leakage_metrics(receipt)
        if receipt.get("corpus_sha256") is None:
            self.finding("LEAKAGE_CORPUS_UNBOUND", "leakage",
                         "Leakage receipt has no corpus_sha256; no hash is inferred")
            return
        corpus = relative(receipt.get("corpus"))
        records = self.corpus(corpus, receipt["corpus_sha256"])
        require(integer(receipt.get("rows"), "leakage.rows", 1) == len(records),
                "ROW_COUNT_MISMATCH", "Leakage rows do not match bound corpus")


def verify_release_receipts(repo_root: Path,
                            receipt_path: str = "out/release_gate.json") -> dict[str, Any]:
    """Return findings for byte binding and recorded consistency; never grant promotion."""
    verifier = Verifier(Path(repo_root))
    release: dict[str, Any] = {}
    results: dict[str, str] = {}
    try:
        release = verifier.document(receipt_path)
        require(release.get("schema") in (None, "szl.release-gate/v2"), "RELEASE_SCHEMA",
                "Expected szl.release-gate/v2 or the legacy unversioned three-stage receipt")
        stages = object_value(release.get("stages"), "stages")
        require(set(stages) == STAGES, "STAGE_SET",
                "Exactly in_domain, red_team, and leakage stages are required")
        require(release.get("release_verdict") in ("BLOCKED", "PROMOTABLE"), "RELEASE_VERDICT",
                "Explicit release verdict BLOCKED or PROMOTABLE required")
        for name in sorted(STAGES):
            before = len(verifier.findings)
            try:
                stage = object_value(stages[name], name)
                if name == "leakage":
                    verifier.leakage(stage, release.get("schema") == "szl.release-gate/v2")
                else:
                    verifier.model(name, stage)
            except InvalidEvidence as exc:
                verifier.finding(exc.code, name, str(exc))
            except (OSError, UnicodeError) as exc:
                verifier.finding("INPUT_UNREADABLE", name, str(exc))
            results[name] = "PASS" if before == len(verifier.findings) else "FAIL"
        if set(verifier.candidates) == set(MODEL_CORPORA):
            if verifier.candidates["in_domain"] != verifier.candidates["red_team"]:
                verifier.finding("CANDIDATE_ADAPTER_MISMATCH", "release",
                                 "Model stages name different canonical adapter paths")
                results["in_domain"] = results["red_team"] = "FAIL"
        if all(isinstance(stage, dict) and type(stage.get("stage_passed")) is bool
               for stage in stages.values()):
            derived = "PROMOTABLE" if all(stage["stage_passed"] for stage in stages.values()) else "BLOCKED"
            require(release["release_verdict"] == derived, "RELEASE_CONTRADICTION",
                    "Release verdict contradicts recorded stage results")
    except InvalidEvidence as exc:
        verifier.finding(exc.code, "release", str(exc))
    except (OSError, UnicodeError) as exc:
        verifier.finding("INPUT_UNREADABLE", "release", str(exc))
    return {
        "schema": "szl.release-receipt-verification/v1",
        "contract": "szl.release-gate/v2",
        "input_schema": release.get("schema", "legacy-unversioned"),
        "integrity_status": "FAIL" if verifier.findings else "PASS",
        "release_verdict": release.get("release_verdict"),
        "promotion_status": "NOT_PROMOTABLE" if release.get("release_verdict") == "BLOCKED" else "NOT_ESTABLISHED",
        "stages": results,
        "candidate_binding": {
            "status": "PATH_IDENTITY_ONLY",
            "same_declared_candidate": (
                verifier.candidates["in_domain"] == verifier.candidates["red_team"]
                if set(verifier.candidates) == set(MODEL_CORPORA) else None),
            "paths": {name: path.relative_to(verifier.root).as_posix()
                      for name, path in verifier.candidates.items()},
            "adapter_weights_verified": False,
            "limitation": "Path equality does not establish identical adapter weights, base model "
                          "revisions, or the candidate actually used at execution time.",
        },
        "findings": verifier.findings,
        "inputs": sorted(verifier.inputs.values(), key=lambda item: item["path"]),
        "scope": "Recorded consistency and byte binding only; no model rerun, authenticated "
                 "execution, fresh release authorization, or historical receipt repair. "
                 "Leakage metrics are checked for recorded contradictions, not recomputed; "
                 "the rounded Jaccard value cannot establish the unrounded value.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--receipt", default="out/release_gate.json")
    parser.add_argument("--json", action="store_true", help="Print the versioned audit report")
    args = parser.parse_args(argv)
    report = verify_release_receipts(args.repo_root, args.receipt)
    if args.json:
        print(json.dumps(report, indent=2, allow_nan=False))
    else:
        print("RECEIPT INTEGRITY: " + report["integrity_status"])
        for item in report["findings"]:
            print(f"  FAIL {item['stage']} [{item['code']}]: {item['message']}")
        print("RELEASE VERDICT IN RECEIPT: " + str(report["release_verdict"]))
        print("PROMOTION: " + report["promotion_status"])
    return 1 if report["findings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
