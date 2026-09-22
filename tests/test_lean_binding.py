import json
from pathlib import Path

B = json.loads(Path("out/lean_binding.json").read_text(encoding="utf-8-sig"))


def test_nothing_claims_kernel_verification():
    assert B["kernel_verified_count"] == 0
    assert B["kernel_state"] == "UNVERIFIED_LOCALLY"
    for b in B["bindings"]:
        assert b["kernel_verified"] is False


def test_numbering_correction_is_recorded():
    s = B["numbering_correction"]
    assert "SATISFIES A5" in s and "VIOLATES A1" in s
    assert "447 of 895" in s


def test_every_binding_names_a_property():
    for b in B["bindings"]:
        assert b["property"] and len(b["property"]) > 8
        assert b["local"]


def test_supersessions_are_explicit():
    joined = " ".join(B["supersessions"])
    assert "conformal" in joined and "locked_count_eight" in joined and "cap" in joined


def test_ceiling_is_flagged_as_unbound():
    notes = " ".join(b["note"] for b in B["bindings"])
    assert "MY CEILING IS AD HOC" in notes