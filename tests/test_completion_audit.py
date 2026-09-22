import json
from pathlib import Path
C = json.loads(Path("out/completion_audit.json").read_text(encoding="utf-8-sig"))

def test_every_adoption_names_a_target():
    for x in C["artifacts"]:
        if x["decision"] in ("ADOPT_NOW", "ADOPT_NEXT"):
            assert x["target"] not in ("", "-"), x["artifact"] + " adopted with no named gap"
            assert len(x["reason"]) > 30

def test_every_exclusion_states_a_reason():
    for x in C["artifacts"]:
        if x["decision"] == "EXCLUDE":
            assert x["target"] == "-"
            assert len(x["reason"]) > 15

def test_attention_kernels_are_excluded():
    ex = {x["artifact"] for x in C["artifacts"] if x["decision"] == "EXCLUDE"}
    assert "SZLHOLDINGS/YARQA-ATTN" in ex
    assert "SZLHOLDINGS/szl-receipt-attn" in ex

def test_audit_does_not_promise_a_working_classifier():
    assert "nothing on this list makes the engine classify correctly" in C["what_would_make_us_whole"]

def test_no_artifact_is_left_undecided():
    for x in C["artifacts"]:
        assert x["decision"] in ("ADOPT_NOW", "ADOPT_NEXT", "DEFER", "EXCLUDE")