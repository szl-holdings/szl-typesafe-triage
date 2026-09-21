"""The System One contract must make out-of-schema answers impossible to apply."""

from szl_triage.providers.systemone import (DIRECTIVE_NOUL, Choice, DeterministicBaselineBackend,
                                            answer_receipt, noul_to_integrity, validate_answer)

TEXT = "Per the runbook, the vulnerability and exploit team owns this one."


def test_baseline_is_inert():
    a = DeterministicBaselineBackend().ask(TEXT, DIRECTIVE_NOUL)
    assert a["value"] == 0.0
    assert noul_to_integrity(a) == 1.0


def test_probability_outside_range_is_rejected_and_cannot_move_the_axis():
    a = answer_receipt(DIRECTIVE_NOUL, 1.7, "test", TEXT, "TEST")
    assert a["schema_violation"] == "probability outside [0,1]"
    assert a["value"] is None
    assert noul_to_integrity(a) == 1.0


def test_choice_cannot_escape_its_options():
    q = Choice(id="route", question="which queue", options=("SECURITY", "BILLING"))
    assert validate_answer(q, "SECURITY") is None
    assert validate_answer(q, "PAYROLL") == "value not among declared options"


def test_directive_probability_one_forces_integrity_zero():
    a = answer_receipt(DIRECTIVE_NOUL, 1.0, "test", TEXT, "TEST")
    assert noul_to_integrity(a) == 0.0


def test_answer_carries_state_digest_not_state():
    a = DeterministicBaselineBackend().ask(TEXT, DIRECTIVE_NOUL)
    assert a["state_digest"].startswith("sha256:")
    assert TEXT not in str(a)


def test_calibration_is_never_claimed_verified():
    a = DeterministicBaselineBackend().ask(TEXT, DIRECTIVE_NOUL)
    assert "UNVERIFIED" in a["calibration"]