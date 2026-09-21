import json
from pathlib import Path
import pytest

A = Path("out/axiom_conformance.json")
P = Path("out/physics_information.json")
Q = Path("out/open_questions.json")


def _rd(p):
    if not p.exists():
        pytest.skip("receipt not produced in this run: " + str(p))
    return json.loads(p.read_text(encoding="utf-8-sig"))


def test_engine_aggregator_is_not_lambda():
    d = _rd(A)
    assert "NOT the Lutar invariant" in d["central_correction"]
    assert d["violations"]["A5_permutation_invariance"] > 0
    assert d["phi_differs_from_lambda_on"] > 0


def test_a1_to_a4_hold():
    d = _rd(A)
    for k in ("A1_monotonicity", "A2_homogeneity", "A3_idempotence", "A4_boundedness"):
        assert d["violations"][k] == 0, k


def test_uniqueness_is_reported_as_the_thesis_states_it():
    d = _rd(A)
    s = d["uniqueness_status_per_thesis"]
    assert "Conjecture 1" in s and "disproved as stated" in s
    assert "Theorem U" in s and "axiom-free" in s


def test_bounded_loop_is_not_claimed_from_a_cap():
    d = _rd(A)
    assert d["ouroboros_bound_correction"]["state"] in ("FAIL_BY_DEFINITION", "UNAVAILABLE")
    assert "well-founded measure" in d["ouroboros_bound_correction"]["thesis_definition"]


def test_energy_measured_or_null():
    d = _rd(P)
    e = d["energy"]
    assert (e["measured"] and e["joules"] is not None) or (e["joules"] is None and e["state"] == "UNAVAILABLE")


def test_open_questions_cite_receipts():
    d = _rd(Q)
    for x in d["questions"]:
        assert x["receipt"] == "-" or Path(x["receipt"]).exists()