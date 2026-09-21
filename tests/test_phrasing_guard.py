import json
from pathlib import Path

G = json.loads(Path("out/phrasing_guard.json").read_text(encoding="utf-8-sig"))
R = json.loads(Path("out/retractions.json").read_text(encoding="utf-8-sig"))


def test_no_claimed_violations():
    assert G["claimed_violation_count"] == 0, G["claimed_violations"][:6]


def test_four_classes_are_reported():
    for k in ("META", "QUOTED", "DENIED", "CLAIMED"):
        assert k in G["classes"]


def test_meta_exclusions_state_a_reason():
    assert G["meta_exclusions"]
    for k, v in G["meta_exclusions"].items():
        assert len(v) > 40


def test_denied_are_listed_not_hidden():
    assert G["denied_count"] == 0 or G["denied_pending_human_ratification"]
    for d in G["denied_pending_human_ratification"]:
        assert d.get("negation_cue")


def test_guard_states_its_own_limit():
    assert "checks language, not truth" in G["what_the_guard_cannot_do"]
    assert "heuristic" in G["honest_limit"]


def test_iteration_history_is_kept():
    h = G["iteration_history"]
    assert "v2" in h and "v3" in h and "369" in h


def test_lambda_cited_as_conjecture_one():
    c = G["canonical_estate_facts"]["lambda_status"]
    assert "Conjecture 1" in c and "disproved as stated" in c


def test_locked_count_unresolved():
    assert G["canonical_estate_facts"]["locked_set_discrepancy"]["state"] == "UNRESOLVED"


def test_retractions_include_my_own():
    assert R["count"] >= 11 and len(R["retractions_of_my_own_prior_claims_in_this_repo"]) >= 7