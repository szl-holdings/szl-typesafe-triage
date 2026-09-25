# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Adversarial replay checks against copies of the retained study evidence."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from szl_triage.study_evidence import audit_study

STUDY = Path(__file__).resolve().parents[1] / "evidence" / "five-seed-study"


@pytest.fixture
def study(tmp_path):
    target = tmp_path / "study"
    shutil.copytree(STUDY, target)
    return target


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8", newline="\n")


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line]


def write_rows(path, value):
    path.write_text("".join(json.dumps(row) + "\n" for row in value), encoding="utf-8", newline="\n")


def codes(report):
    return {item["code"] for item in report["findings"] if item["severity"] == "error"}


def rebind_prediction_hash(study, name="seed-023"):
    """A forged hash must not be enough to defeat semantic replay."""
    path = study / "evaluation" / f"metrics-{name}.json"
    metric = read(path)
    metric["predictions_sha256"] = hashlib.sha256(
        (study / "evaluation" / f"predictions-{name}.jsonl").read_bytes()).hexdigest()
    write(path, metric)
    aggregate_path = study / "evaluation" / "aggregate_metrics.json"
    aggregate = read(aggregate_path)
    aggregate["targets"] = [metric if target["name"] == name else target
                            for target in aggregate["targets"]]
    write(aggregate_path, aggregate)


def test_real_evidence_replays_without_promotion_or_writes():
    before = {path: path.read_bytes() for path in STUDY.rglob("*") if path.is_file()}
    report = audit_study(STUDY)
    assert report["integrity_status"] == "PASS", report["findings"]
    assert report["promotion_status"] == "NOT_PROMOTABLE"
    assert report["artifact_verification"]["status"] == "NOT_REQUESTED"
    assert report["release_gate"]["status"] == "NOT_SUPPLIED"
    assert report["provenance"]["model_rerun"] is False
    assert report["provenance"]["authenticated_execution"] is False
    assert report["provenance"]["missing_bindings"]["seed-011"]
    replay = report["replay"]
    assert replay["held_rows"] == 113
    assert replay["train_rows"] == 515
    assert replay["runs"]["base"]["strict_json"] == 0
    assert replay["runs"]["base"]["failure_rows"] == 113
    assert replay["runs"]["seed-011"]["target_evidence_exact"] == 112
    assert len(replay["runs"]["seed-011"]["target_evidence_mismatch_row_ids"]) == 1
    assert replay["runs"]["seed-011"]["failure_rows"] == 0
    assert replay["five_seed_summary"]["target_evidence_exact_rate"]["mean"] == pytest.approx(564 / 565)
    assert before == {path: path.read_bytes() for path in before}
    assert report["bundle_sha256"] == audit_study(STUDY)["bundle_sha256"]


def test_raw_output_changed_even_with_recomputed_hashes_is_rejected(study):
    path = study / "evaluation" / "predictions-seed-023.jsonl"
    predictions = rows(path)
    forged = json.loads(predictions[0]["raw_output"])
    forged["label"] = "FORGED_LABEL"
    predictions[0]["raw_output"] = json.dumps(forged)
    write_rows(path, predictions)
    rebind_prediction_hash(study)
    report = audit_study(study)
    assert report["integrity_status"] == "FAIL"
    assert "EVALUATION_HASH_MISMATCH" not in codes(report)
    assert {"PREDICTION_REPLAY_MISMATCH", "METRIC_REPLAY_MISMATCH", "FAILURE_SET_MISMATCH"} <= codes(report)


def test_saved_parsed_and_flags_are_not_trusted(study):
    path = study / "evaluation" / "predictions-seed-023.jsonl"
    predictions = rows(path)
    predictions[0]["parsed"]["label"] = "SECURITY"
    predictions[0]["label_exact"] = False
    predictions[0]["grounded_evidence_flags"] = [False]
    write_rows(path, predictions)
    rebind_prediction_hash(study)
    report = audit_study(study)
    assert "PREDICTION_REPLAY_MISMATCH" in codes(report)
    assert report["replay"]["runs"]["seed-023"]["label_exact"] == 113


@pytest.mark.parametrize("change", ["duplicate", "missing", "unknown", "target", "family"])
def test_prediction_coverage_and_row_bindings(study, change):
    path = study / "evaluation" / "predictions-seed-023.jsonl"
    predictions = rows(path)
    if change == "duplicate":
        predictions[1] = predictions[0]
    elif change == "missing":
        predictions.pop()
    elif change == "unknown":
        predictions[0]["row_id"] = "0" * 64
    elif change == "target":
        predictions[0]["target"]["label"] = "FORGED"
    else:
        predictions[0]["family"] = "0" * 10
    write_rows(path, predictions)
    rebind_prediction_hash(study)
    report = audit_study(study)
    assert report["integrity_status"] == "FAIL"
    assert codes(report) & {"DUPLICATE_PREDICTION", "PREDICTION_COVERAGE", "PREDICTION_BINDING"}


@pytest.mark.parametrize("change", ["duplicate", "missing", "extra", "wrong_identity"])
def test_run_set_is_exact(study, change):
    aggregate_path = study / "evaluation" / "aggregate_metrics.json"
    aggregate = read(aggregate_path)
    if change == "duplicate":
        aggregate["targets"][-1] = aggregate["targets"][1]
        write(aggregate_path, aggregate)
    elif change == "missing":
        (study / "evaluation" / "metrics-seed-071.json").unlink()
    elif change == "extra":
        shutil.copyfile(study / "evaluation" / "metrics-seed-071.json",
                        study / "evaluation" / "metrics-seed-999.json")
    else:
        path = study / "evaluation" / "metrics-seed-071.json"
        value = read(path)
        value["name"] = "seed-011"
        write(path, value)
    report = audit_study(study)
    assert report["integrity_status"] == "FAIL"
    assert codes(report) & {"RUN_SET", "RUN_FILE_SET", "RUN_IDENTITY"}


def test_stale_aggregate_summary_rejected(study):
    path = study / "evaluation" / "aggregate_metrics.json"
    value = read(path)
    value["five_seed_summary"]["target_evidence_exact_rate"]["mean"] = 1.0
    write(path, value)
    assert "AGGREGATE_SUMMARY_MISMATCH" in codes(audit_study(study))


def test_stale_aggregate_target_rejected(study):
    path = study / "evaluation" / "aggregate_metrics.json"
    value = read(path)
    value["targets"][1]["target_evidence_exact"] = 113
    write(path, value)
    assert "AGGREGATE_TARGET_MISMATCH" in codes(audit_study(study))


def test_failure_set_cannot_omit_failed_rows(study):
    path = study / "evaluation" / "failures-base.jsonl"
    write_rows(path, rows(path)[1:])
    metric_path = study / "evaluation" / "metrics-base.json"
    value = read(metric_path)
    value["failures_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    write(metric_path, value)
    assert "FAILURE_SET_MISMATCH" in codes(audit_study(study))


def test_frozen_hash_tampering_detected(study):
    path = study / "frozen" / "held.jsonl"
    value = rows(path)
    value[0]["prompt"] = "Fabricated new prompt"
    write_rows(path, value)
    assert "FROZEN_HASH_MISMATCH" in codes(audit_study(study))


def test_split_overlap_even_with_rebound_manifest(study):
    train_path = study / "frozen" / "train.jsonl"
    train = rows(train_path)
    held = rows(study / "frozen" / "held.jsonl")
    train[0]["row_id"] = held[0]["row_id"]
    train[0]["family"] = held[0]["family"]
    write_rows(train_path, train)
    manifest_path = study / "frozen" / "experiment_manifest.json"
    manifest = read(manifest_path)
    manifest["train_manifest_sha256"] = hashlib.sha256(train_path.read_bytes()).hexdigest()
    write(manifest_path, manifest)
    assert "SPLIT_ROW_OVERLAP" in codes(audit_study(study))


def test_duplicate_seed_in_index_rejected(study):
    path = study / "adapter-index.json"
    value = read(path)
    value[-1]["seed"] = 11
    write(path, value)
    assert "SEED_SET" in codes(audit_study(study))


def test_training_hparams_must_match_except_seed(study):
    path = study / "training" / "training_receipt-seed-071.json"
    value = read(path)
    value["hyperparameters"]["lr"] = 0.5
    write(path, value)
    assert "TRAINING_HPARAM_MISMATCH" in codes(audit_study(study))


@pytest.mark.parametrize("field,value", [("state", "CLAIMED"), ("status", "PASS"),
                                         ("lora_b_total", 0), ("lora_b_nonzero", 0),
                                         ("lora_b_total", True), ("lora_b_nonzero", 96.0)])
def test_training_binding_corroborates_measured_state_and_counts(study, field, value):
    path = study / "training" / "training_receipt-seed-071.json"
    receipt = read(path)
    receipt[field] = value
    write(path, receipt)
    report = audit_study(study)
    assert report["integrity_status"] == "FAIL"
    assert codes(report) & {"TRAINING_STATE_MISMATCH", "TRAINING_BINDING_FAILED", "SCHEMA_TYPE"}


@pytest.mark.parametrize("payload,expected", [
    ("{broken", "MALFORMED_JSON"),
    ('{"schema":"szl.five-seed-aggregate/v1","schema":"bogus"}', "DUPLICATE_JSON_KEY"),
    ('{"value":NaN}', "NONFINITE_VALUE"),
    ('{"value":1e999}', "NONFINITE_VALUE"),
    pytest.param('{"value":' + "9" * 1000 + '}', "NUMBER_RANGE", id="oversized-integer"),
    ("[]", "SCHEMA_TYPE"),
    ('{"schema":"unknown"}', "SCHEMA_VERSION"),
])
def test_malformed_evidence_fails_closed(study, payload, expected):
    (study / "evaluation" / "aggregate_metrics.json").write_text(payload, encoding="utf-8")
    report = audit_study(study)
    assert report["integrity_status"] == "FAIL"
    assert expected in codes(report)


@pytest.mark.parametrize("field,value", [("strict_json", True), ("held_rows", "113"),
                                         ("joint_accuracy", True), ("median_latency_seconds", -1)])
def test_metric_types_cannot_coerce_into_valid_values(study, field, value):
    path = study / "evaluation" / "metrics-seed-023.json"
    metric = read(path)
    metric[field] = value
    write(path, metric)
    assert audit_study(study)["integrity_status"] == "FAIL"


def gate_payload(passed):
    return {"release_verdict": "PROMOTABLE" if passed else "BLOCKED", "stages": {
        name: {"stage_passed": passed, "exit": 0 if passed else 1,
               "breaches": {} if passed else {"verdict": "REFUSED"}}
        for name in ("in_domain", "red_team", "leakage")}}


def test_unrelated_status_is_not_a_release_gate(study, tmp_path):
    path = tmp_path / "unrelated.json"
    write(path, {"status": "PASS", "promotion_status": "PROMOTABLE"})
    report = audit_study(study, release_gate=path)
    assert "RELEASE_GATE_SCHEMA" in codes(report)
    assert report["release_gate"]["status"] == "INVALID"
    assert report["promotion_status"] == "NOT_PROMOTABLE"


def test_gate_receipt_reported_without_claiming_fresh_binding(study, tmp_path):
    path = tmp_path / "gate.json"
    write(path, gate_payload(False))
    report = audit_study(study, release_gate=path)
    assert report["integrity_status"] == "PASS"
    assert report["release_gate"]["reported"] == "BLOCKED"
    assert report["release_gate"]["status"] == "REPORTED_UNBOUND"


def test_passing_unbound_gate_cannot_promote(study, tmp_path):
    path = tmp_path / "gate.json"
    write(path, gate_payload(True))
    report = audit_study(study, release_gate=path)
    assert report["integrity_status"] == "PASS"
    assert report["release_gate"]["reported"] == "PROMOTABLE"
    assert report["promotion_status"] == "NOT_PROMOTABLE"


def test_contradictory_gate_fails(study, tmp_path):
    path = tmp_path / "gate.json"
    gate = gate_payload(False)
    gate["release_verdict"] = "PROMOTABLE"
    write(path, gate)
    assert "RELEASE_GATE_CONTRADICTION" in codes(audit_study(study, release_gate=path))


@pytest.mark.parametrize("path", ["../escape", "C:/escape", "\\\\server\\share", "out/../../escape", "out/file:stream"])
def test_adapter_paths_cannot_escape_root(study, tmp_path, path):
    index_path = study / "adapter-index.json"
    value = read(index_path)
    value[0]["local_path"] = path
    write(index_path, value)
    report = audit_study(study, artifact_root=tmp_path)
    assert "UNSAFE_PATH" in codes(report)
    assert report["artifact_verification"]["status"] == "FAILED"


def make_fake_artifacts(study, root):
    """Byte verification fixture only: these are intentionally not loadable adapters."""
    index_path = study / "adapter-index.json"
    index = read(index_path)
    for entry in index:
        directory = root / entry["local_path"]
        directory.mkdir(parents=True)
        data = ("synthetic adapter bytes seed " + str(entry["seed"])).encode()
        (directory / "adapter_model.safetensors").write_bytes(data)
        entry["adapter_sha256"] = hashlib.sha256(data).hexdigest()
        write(directory / "adapter_config.json", {
            "base_model_name_or_path": "unsloth/Qwen3.5-0.8B", "r": 16,
            "lora_alpha": 16, "lora_dropout": 0.0, "peft_type": "LORA"})
    write(index_path, index)
    return index


def test_optional_local_adapter_bytes_and_configuration(study, tmp_path):
    root = tmp_path / "artifacts"
    make_fake_artifacts(study, root)
    report = audit_study(study, artifact_root=root)
    assert report["integrity_status"] == "PASS", report["findings"]
    assert report["artifact_verification"]["status"] == "VERIFIED"
    assert report["artifact_verification"]["verified_seeds"] == [11, 23, 37, 53, 71]
    assert report["provenance"]["model_rerun"] is False
    assert report["promotion_status"] == "NOT_PROMOTABLE"


@pytest.mark.parametrize("tamper", ["bytes", "config", "missing"])
def test_local_adapter_tampering_fails(study, tmp_path, tamper):
    root = tmp_path / "artifacts"
    index = make_fake_artifacts(study, root)
    directory = root / index[0]["local_path"]
    if tamper == "bytes":
        (directory / "adapter_model.safetensors").write_bytes(b"tampered")
    elif tamper == "config":
        path = directory / "adapter_config.json"
        value = read(path)
        value["r"] = 32
        write(path, value)
    else:
        (directory / "adapter_model.safetensors").unlink()
    report = audit_study(study, artifact_root=root)
    assert report["integrity_status"] == "FAIL"
    assert report["artifact_verification"]["status"] == "FAILED"
    assert codes(report) & {"ADAPTER_HASH_MISMATCH", "ADAPTER_CONFIG_MISMATCH", "INPUT_UNREADABLE"}


def test_missing_evidence_returns_named_failure(tmp_path):
    report = audit_study(tmp_path / "missing")
    assert report["integrity_status"] == "FAIL"
    assert report["promotion_status"] == "NOT_ESTABLISHED"
    assert "INPUT_UNREADABLE" in codes(report)


def test_bundle_fingerprint_tracks_examined_bytes(study):
    original = audit_study(study)
    path = study / "training" / "training_receipt-seed-011.json"
    # Whitespace is semantically inert but still changes the examined byte identity.
    path.write_bytes(path.read_bytes() + b"\n")
    changed = audit_study(study)
    assert changed["integrity_status"] == "PASS"
    assert changed["bundle_sha256"] != original["bundle_sha256"]
