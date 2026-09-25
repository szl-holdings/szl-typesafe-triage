# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Adversarial verification of tiny synthetic receipts; no real evidence is rewritten."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_release_receipts.py"
SPEC = importlib.util.spec_from_file_location("release_receipt_verifier", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
verify = MODULE.verify_release_receipts


def write(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8", newline="\n")
    return path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def bound(tmp_path):
    for name in MODULE.MODEL_CORPORA.values():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"input":"fixture","label":"BUG","state":"MEASURED"}\n',
                        encoding="utf-8", newline="\n")
    stages = {}
    for name, corpus in MODULE.MODEL_CORPORA.items():
        stages[name] = {"exit": 0, "verdict": "PROMOTABLE", "rows": 1,
                        "label_ok": 1, "state_ok": 1, "adapter": "out/fixture-adapter",
                        "data_path": corpus, "corpus_sha256": sha(tmp_path / corpus),
                        "breaches": {}, "stage_passed": True}
    leakage = {"schema": "szl.leakage-gate/v1", "status": "MEASURED", "commit": "a" * 40,
               "corpus": MODULE.MODEL_CORPORA["in_domain"], "rows": 1,
               "corpus_sha256": stages["in_domain"]["corpus_sha256"],
               "verdict": "REFUSED", "semantic_pass": "UNAVAILABLE",
               "template_families": 1, "largest_family": 1,
               "exact_duplicates_across_split": 0, "shared_template_families": 0,
               "max_char5gram_jaccard": 0.0,
               "reasons": ["Only one template family; at least eight are required"]}
    sidecar = write(tmp_path, "out/leakage_gate.json", leakage)
    stages["leakage"] = {"exit": 1, "verdict": "REFUSED", "stage_passed": False,
                         "breaches": {"semantic_pass": "UNAVAILABLE"}, "commit": "a" * 40,
                         "receipt_path": "out/leakage_gate.json", "receipt_sha256": sha(sidecar)}
    report = {"schema": "szl.release-gate/v2", "release_verdict": "BLOCKED", "stages": stages}
    write(tmp_path, "out/release_gate.json", report)
    return tmp_path, report


def run(bound):
    root, report = bound
    write(root, "out/release_gate.json", report)
    return verify(root)


def codes(report):
    return {item["code"] for item in report["findings"]}


def test_bound_negative_receipt_is_integrity_valid_and_still_blocked(bound):
    report = run(bound)
    assert report["integrity_status"] == "PASS", report["findings"]
    assert report["release_verdict"] == "BLOCKED"
    assert report["promotion_status"] == "NOT_PROMOTABLE"
    assert report["stages"] == dict.fromkeys(MODULE.STAGES, "PASS")
    assert report["candidate_binding"]["status"] == "PATH_IDENTITY_ONLY"
    assert report["candidate_binding"]["adapter_weights_verified"] is False


def test_model_stages_must_name_same_candidate(bound):
    bound[1]["stages"]["red_team"]["adapter"] = "out/different-adapter"
    report = run(bound)
    assert "CANDIDATE_ADAPTER_MISMATCH" in codes(report)
    assert report["candidate_binding"]["same_declared_candidate"] is False


def test_equivalent_adapter_path_spelling_is_same_declaration(bound):
    bound[1]["stages"]["red_team"]["adapter"] = "out\\.\\fixture-adapter"
    report = run(bound)
    assert report["integrity_status"] == "PASS"
    assert report["candidate_binding"]["same_declared_candidate"] is True


@pytest.fixture
def clean(bound):
    """Synthetic internally consistent positive control; no real inference is claimed."""
    root, report = bound
    for name, corpus in MODULE.MODEL_CORPORA.items():
        path = root / corpus
        path.write_text("".join(json.dumps({"input": "fixture " + str(i)}) + "\n"
                                for i in range(16)), encoding="utf-8", newline="\n")
        report["stages"][name].update({"rows": 16, "label_ok": 16, "state_ok": 16,
                                      "corpus_sha256": sha(path)})
    path = root / "out/leakage_gate.json"
    leakage = json.loads(path.read_text())
    leakage.update({"rows": 16, "template_families": 16, "largest_family": 1,
                    "verdict": "CLEAN", "semantic_pass": "PASS", "reasons": [],
                    "corpus_sha256": report["stages"]["in_domain"]["corpus_sha256"]})
    stage = report["stages"]["leakage"]
    stage.update({"receipt_sha256": sha(write(root, "out/leakage_gate.json", leakage)),
                  "exit": 0, "verdict": "CLEAN", "stage_passed": True, "breaches": {}})
    report["release_verdict"] = "PROMOTABLE"
    return bound


def test_consistent_clean_control_does_not_grant_promotion(clean):
    report = run(clean)
    assert report["integrity_status"] == "PASS", report["findings"]
    assert report["promotion_status"] == "NOT_ESTABLISHED"
    assert report["candidate_binding"]["adapter_weights_verified"] is False


@pytest.mark.parametrize("field,value", [("exact_duplicates_across_split", 5),
                                         ("shared_template_families", 5),
                                         ("max_char5gram_jaccard", 1.0),
                                         ("reasons", ["Known contamination"]),
                                         ("template_families", 7)])
def test_rehashed_clean_receipt_with_refusing_metrics_is_rejected(clean, field, value):
    root, report = clean
    path = root / "out/leakage_gate.json"
    leakage = json.loads(path.read_text())
    leakage[field] = value
    if field == "template_families":
        leakage["largest_family"] = 10
    report["stages"]["leakage"]["receipt_sha256"] = sha(write(root, "out/leakage_gate.json", leakage))
    observed = run(clean)
    assert "LEAKAGE_METRIC_CONTRADICTION" in codes(observed)
    assert observed["integrity_status"] == "FAIL"


@pytest.mark.parametrize("field,value", [("exact_duplicates_across_split", True),
                                         ("shared_template_families", -1),
                                         ("max_char5gram_jaccard", "0.2"),
                                         ("max_char5gram_jaccard", 1.1),
                                         ("reasons", "none"), ("rows", 0)])
def test_leakage_metric_types_and_bounds(clean, field, value):
    root, report = clean
    path = root / "out/leakage_gate.json"
    leakage = json.loads(path.read_text())
    leakage[field] = value
    report["stages"]["leakage"]["receipt_sha256"] = sha(write(root, "out/leakage_gate.json", leakage))
    assert run(clean)["integrity_status"] == "FAIL"


def test_clean_jaccard_boundary_is_unchanged(clean):
    root, report = clean
    path = root / "out/leakage_gate.json"
    leakage = json.loads(path.read_text())
    leakage["max_char5gram_jaccard"] = 0.70
    report["stages"]["leakage"]["receipt_sha256"] = sha(write(root, "out/leakage_gate.json", leakage))
    assert run(clean)["integrity_status"] == "PASS"


def test_real_history_is_bound_and_still_not_promotable():
    """Committed artifacts cite measured bytes. Binding must not grant promotion."""
    paths = [ROOT / "out" / name for name in ("release_gate.json", "leakage_gate.json", "release_seal.json")]
    before = {path: path.read_bytes() for path in paths}
    report = verify(ROOT)
    assert report["integrity_status"] == "PASS", report["findings"]
    assert report["release_verdict"] == "BLOCKED"
    assert report["promotion_status"] == "NOT_PROMOTABLE"
    assert report["stages"] == dict.fromkeys(MODULE.STAGES, "PASS")
    gate = json.loads((ROOT / "out" / "release_gate.json").read_text(encoding="utf-8"))
    red = gate["stages"]["red_team"]
    assert red["data_path"].replace("\\", "/") == "policies/redteam_probes.verified.jsonl"
    assert red["verdict"] == "BLOCKED" and red["stage_passed"] is False
    assert red["corpus_sha256"] == hashlib.sha256(
        (ROOT / "policies" / "redteam_probes.verified.jsonl").read_bytes()).hexdigest()
    leakage = json.loads((ROOT / "out" / "leakage_gate.json").read_text(encoding="utf-8"))
    assert leakage["corpus_sha256"] == hashlib.sha256(
        (ROOT / "output" / "triage_distill_v0.5.1.jsonl").read_bytes()).hexdigest()
    assert gate["stages"]["leakage"]["receipt_sha256"] == hashlib.sha256(
        (ROOT / "out" / "leakage_gate.json").read_bytes()).hexdigest()
    assert gate["stages"]["leakage"]["commit"] == leakage["commit"] == "5a45f66"
    assert before == {path: path.read_bytes() for path in paths}


@pytest.mark.parametrize("change", ["empty", "missing", "extra", "not-object"])
def test_exact_three_stage_contract(bound, change):
    report = bound[1]
    if change == "empty":
        report["stages"] = {}
    elif change == "missing":
        del report["stages"]["leakage"]
    elif change == "extra":
        report["stages"]["unknown"] = {}
    else:
        report["stages"] = []
    observed = run(bound)
    assert observed["integrity_status"] == "FAIL"
    assert codes(observed) & {"STAGE_SET", "FIELD_TYPE"}


def test_red_team_cannot_repeat_in_domain_receipt(bound):
    bound[1]["stages"]["red_team"] = dict(bound[1]["stages"]["in_domain"])
    assert "STAGE_CORPUS_MISMATCH" in codes(run(bound))


@pytest.mark.parametrize("key,value", [("rows", True), ("exit", False), ("rows", "1"),
                                      ("rows", 0), ("label_ok", 2), ("label_ok", -1),
                                      ("state_ok", None), ("stage_passed", 1),
                                      ("breaches", []), ("verdict", "NOT_PROMOTABLE")])
def test_stage_types_and_counts_fail_closed(bound, key, value):
    bound[1]["stages"]["in_domain"][key] = value
    assert run(bound)["integrity_status"] == "FAIL"


def test_missing_stage_flag_is_not_false_by_default(bound):
    del bound[1]["stages"]["leakage"]["stage_passed"]
    assert "FIELD_TYPE" in codes(run(bound))


@pytest.mark.parametrize("path", ["", ".", "../escape", "C:\\escape", "\\\\host\\share",
                                 "out/file:stream"])
def test_paths_are_nonempty_relative_and_contained(bound, path):
    bound[1]["stages"]["in_domain"]["data_path"] = path
    assert run(bound)["integrity_status"] == "FAIL"


def test_exact_corpus_bytes_are_hashed_without_newline_normalization(bound):
    root, _ = bound
    path = root / MODULE.MODEL_CORPORA["in_domain"]
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert "CORPUS_HASH_MISMATCH" in codes(run(bound))


def test_rows_are_counted_from_bound_nontraining_records(bound):
    root, report = bound
    path = root / MODULE.MODEL_CORPORA["in_domain"]
    path.write_bytes(path.read_bytes() * 2)
    report["stages"]["in_domain"]["corpus_sha256"] = sha(path)
    assert "ROW_COUNT_MISMATCH" in codes(run(bound))


@pytest.mark.parametrize("key", ["receipt_sha256", "commit"])
def test_missing_leakage_binding_cannot_be_inferred(bound, key):
    del bound[1]["stages"]["leakage"][key]
    report = run(bound)
    assert report["integrity_status"] == "FAIL"
    assert codes(report) & {"LEAKAGE_RECEIPT_UNBOUND", "LEAKAGE_COMMIT_UNBOUND"}


def test_swapped_leakage_sidecar_is_rejected(bound):
    root, _ = bound
    path = root / "out/leakage_gate.json"
    value = json.loads(path.read_text())
    value["commit"] = "b" * 40
    write(root, "out/leakage_gate.json", value)
    assert "LEAKAGE_RECEIPT_HASH_MISMATCH" in codes(run(bound))


def test_rehashed_wrong_commit_still_rejected(bound):
    root, report = bound
    path = root / "out/leakage_gate.json"
    value = json.loads(path.read_text())
    value["commit"] = "b" * 40
    report["stages"]["leakage"]["receipt_sha256"] = sha(write(root, "out/leakage_gate.json", value))
    assert "LEAKAGE_COMMIT_MISMATCH" in codes(run(bound))


def test_unavailable_semantic_evidence_cannot_pass(bound):
    root, report = bound
    path = root / "out/leakage_gate.json"
    value = json.loads(path.read_text())
    value["verdict"] = "CLEAN"
    stage = report["stages"]["leakage"]
    stage.update({"receipt_sha256": sha(write(root, "out/leakage_gate.json", value)),
                  "exit": 0, "verdict": "CLEAN", "stage_passed": True, "breaches": {}})
    report["release_verdict"] = "PROMOTABLE"
    observed = run(bound)
    assert "LEAKAGE_SEMANTIC_NOT_PASS" in codes(observed)
    assert observed["promotion_status"] == "NOT_ESTABLISHED"


def test_contradictory_release_verdict_rejected(bound):
    bound[1]["release_verdict"] = "PROMOTABLE"
    assert "RELEASE_CONTRADICTION" in codes(run(bound))


@pytest.mark.parametrize("raw", ['[]', '{}', '{bad', '{"stages":{},"stages":{}}',
                                  '{"x":NaN}', '{"x":1e999}'])
def test_malformed_input_is_an_error_report_not_traceback(tmp_path, raw):
    (tmp_path / "out").mkdir()
    (tmp_path / "out/release_gate.json").write_text(raw, encoding="utf-8")
    assert verify(tmp_path)["integrity_status"] == "FAIL"


def test_cli_json_report_is_nonzero_on_missing_file(tmp_path):
    result = subprocess.run([sys.executable, "-I", str(SCRIPT), "--repo-root", str(tmp_path), "--json"],
                            capture_output=True, text=True, check=False, timeout=15)
    assert result.returncode == 1
    assert json.loads(result.stdout)["integrity_status"] == "FAIL"
    assert "Traceback" not in result.stderr


def test_import_does_not_run_verification_or_write(tmp_path):
    result = subprocess.run([sys.executable, "-I", "-c",
                             "import runpy; runpy.run_path(" + repr(str(SCRIPT)) + ")"],
                            cwd=tmp_path, capture_output=True, text=True, timeout=15, check=False)
    assert result.returncode == 0
    assert result.stdout == result.stderr == ""
    assert list(tmp_path.iterdir()) == []


def test_release_workflow_pins_history_and_keeps_promotable_gate():
    text = (ROOT / ".github/workflows/release_receipts.yml").read_text()
    refs = re.findall(r"(?m)^\s*- uses:\s*([^\s#]+)", text)
    assert sorted(refs) == sorted([
        "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
        "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"] * 3)
    assert "permissions:\n  contents: read" in text
    assert text.count("persist-credentials: false") == 3
    assert text.count("timeout-minutes: 5") == 3
    seal = text.split("  verify-seal:")[1].split("  release-promotable:")[0]
    assert "fetch-depth: 0" in seal
    assert "python scripts/verify_release_receipts.py" in text
    assert 'if verdict == "BLOCKED":' in text
    assert 'print("PROMOTION: NOT_PROMOTABLE")' in text
    assert 'if verdict == "PROMOTABLE":' in text
    assert 'print("PROMOTION: NOT_ESTABLISHED")' in text
    assert 'sys.exit(0 if r.get("release_verdict") == "PROMOTABLE" else 1)' not in text
    assert "continue-on-error" not in text
    assert "|| true" not in text
