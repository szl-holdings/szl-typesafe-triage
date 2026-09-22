import json
from pathlib import Path
C = json.loads(Path("out/yarqa_compartments.json").read_text(encoding="utf-8"))
INV = {i["id"]: i for i in C["invariants_i1_i8"]}

def test_flow_balances():
    assert C["unaccounted"] == 0 and C["multiply_assigned"] == 0
    assert sum(C["compartments"].values()) == C["inflow"]
    assert C["mass_balance_holds"] is True

def test_bypass_is_reported():
    assert C["bypass_rows"] > 0 and 0.0 < C["bypass_fraction"] < 1.0
    assert "around the aggregator" in C["why_bypass_matters"]

def test_all_eight_invariants_present_with_legal_states():
    for i in ("I1", "I2", "I3", "I4", "I5", "I6", "I7", "I8"):
        assert INV[i]["state"] in ("PASS", "PARTIAL", "FAIL", "UNAVAILABLE")

def test_i6_is_evidence_derived():
    assert "never asserted" in INV["I6"]["detail"]

def test_attention_kernel_excluded():
    assert "YARQA-ATTN attention kernel" in C["borrowed_from"]