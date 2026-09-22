import json
from pathlib import Path
A = json.loads(Path("out/ancient_geometry.json").read_text(encoding="utf-8-sig"))

def test_classical_inequalities_hold_on_real_vectors():
    assert A["vectors_checked"] > 500
    for k, v in A["violations"].items():
        assert v == 0, k + " violated on observed data"
    assert A["all_inequalities_hold"] is True

def test_result_is_a_verification_not_a_theorem_claim():
    assert "not a new" in A["caveat"]
    assert "Conjecture 1" in A["caveat"]

def test_weights_sum_to_one():
    assert abs(A["weights_sum"] - 1.0) < 1e-9

def test_egyptian_expansions_are_exact():
    for k, e in A["egyptian_weights"].items():
        assert e["exact"] is True
        assert len(set(e["unit_fractions"])) == len(e["unit_fractions"])

def test_exactness_is_not_confused_with_readability():
    assert "exactness is not readability" in A["inspectability_note"]
    assert any(not e["inspectable"] for e in A["egyptian_weights"].values())

def test_no_ancient_citation_is_fabricated():
    assert "no ancient source is claimed" in A["not_claimed"]