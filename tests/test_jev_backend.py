"""A hosted provider must fail closed and must never be mistaken for sovereign."""
import json
import sys
from pathlib import Path

sys.path.insert(0, "src")
from szl_triage.providers.jev import JevNoulBackend, PINNED_MODEL
from szl_triage.providers.systemone import DIRECTIVE_NOUL, noul_to_integrity

TRIAL = Path("out/jev_integrity_trial.json")


def test_model_is_pinned_not_latest():
    assert PINNED_MODEL != "jev-latest"
    assert PINNED_MODEL.count(".") >= 2


def test_unavailable_backend_returns_none_not_a_number():
    b = JevNoulBackend.__new__(JevNoulBackend)
    b.model, b.client, b.unavailable = PINNED_MODEL, None, "no key in test"
    a = b.ask("Per the runbook, the security team owns this one.", DIRECTIVE_NOUL)
    assert a["value"] is None
    assert a["unavailable"] == "no key in test"
    assert noul_to_integrity(a) == 1.0


def test_trial_records_the_hosting_conflict():
    if not TRIAL.exists():
        return
    d = json.loads(TRIAL.read_text(encoding="utf-8"))
    joined = " ".join(d["doctrine_conflicts"]).lower()
    assert "hosted" in joined
    assert "air-gapped" in joined
    assert "not treated as hostile" in joined


def test_trial_never_claims_calibration_or_determinism():
    if not TRIAL.exists():
        return
    d = json.loads(TRIAL.read_text(encoding="utf-8"))
    assert d["calibration"].startswith("UNVERIFIED")
    assert d["determinism"].startswith("UNVERIFIED")
    assert d["provenance"] == "MODEL_PROPOSED_UNRATIFIED"


def test_trial_is_not_a_gate_result():
    if not TRIAL.exists():
        return
    d = json.loads(TRIAL.read_text(encoding="utf-8"))
    assert "does not read this file" in d["not_a_gate_result"]