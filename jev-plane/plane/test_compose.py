"""Compose must fail closed: a missing, NaN or infinite answer is UNAVAILABLE, never a clean label.

Run: python -m pytest jev-plane/plane -ra
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "plane" / "compose.py"
sys.path.insert(0, str(ROOT / "plane"))

import compose as plane  # noqa: E402

PACK_KEYS = {
    "szl.origin_claim.v1": ("surface_role", "claim_overreach", "count_unbound",
                            "origin_confusion", "honesty_severity"),
    "szl.hub_card.v1": ("artifact_class", "unsafe_serialization", "promotion_language",
                        "decommissioned_as_live", "evidence_grade"),
    "szl.github_item.v1": ("kind", "claim_risk", "secret_risk", "actionable",
                           "ready_to_merge", "urgency"),
    "szl.router_intent.v1": ("handler", "needs_yuyay", "stakes", "prompt_injection"),
    "szl.overclaim_reader.v1": (
        "evidence_class",
        "claims_live",
        "invents_joules",
        "treats_hf_as_source",
        "lambda_as_theorem",
        "unsigned_as_live",
        "overclaim_severity",
    ),
}
FIXTURE_FOR_PACK = {
    "szl.origin_claim.v1": "origin_honest_ok.json",
    "szl.hub_card.v1": "hub_lora_candidate.json",
    "szl.github_item.v1": "github_11_12.json",
    "szl.router_intent.v1": "router_refuse_gates.json",
    "szl.overclaim_reader.v1": "overclaim_measured_ok.json",
}
NON_FINITE = (float("nan"), float("inf"), float("-inf"))
NOT_NUMBERS = (None, "0.9", True, [0.9], {"v": 0.9})


def run(fixture: str) -> dict:
    raw = (ROOT / "fixtures" / fixture).read_text(encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(COMPOSE)],
        input=raw,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(proc.stdout)


def fixture_answers(fixture: str) -> dict:
    return json.loads((ROOT / "fixtures" / fixture).read_text(encoding="utf-8"))["answers"]


def assert_advisory(decision: dict) -> None:
    assert decision["advisory"] is True
    assert decision["jev_allow_alone"] is False
    assert decision["auto_merge"] is False
    assert decision["auto_close"] is False


# --- existing fixture behaviour, now collected by pytest -------------------------------------

def test_origin_honest_ok_labels_and_does_not_block():
    honest = run("origin_honest_ok.json")["decision"]
    assert honest["action"] == "label", honest
    assert honest["block_publish"] is False
    assert honest["reader_status"] == "OK"
    assert_advisory(honest)


def test_origin_count_drift_blocks_publish():
    drift = run("origin_count_drift.json")["decision"]
    assert drift["block_publish"] is True, drift
    assert drift["action"] == "block_publish"


def test_hub_lora_candidate_is_labelled_not_blocked():
    lora = run("hub_lora_candidate.json")["decision"]
    assert "hub:weights_candidate" in lora["labels"], lora
    assert lora["block_publish"] is False


def test_github_11_12_is_governance_and_held():
    gate = run("github_11_12.json")["decision"]
    assert "governance" in gate["labels"], gate
    assert gate["block_merge"] is True
    assert gate["auto_merge"] is False


def test_router_refuse_gates_refuses():
    refuse = run("router_refuse_gates.json")["decision"]
    assert refuse["refuse"] is True
    assert refuse["action"] == "refuse"
    assert refuse["jev_allow_alone"] is False


# --- accessors: None on missing, NaN, +/-Inf, non-numeric, out of range ----------------------

@pytest.mark.parametrize("bad", NON_FINITE + NOT_NUMBERS + (-0.01, 1.01))
def test_noul_is_none_on_unusable_input(bad):
    assert plane.noul({"k": {"type": "noul", "noul": bad}}, "k") is None


@pytest.mark.parametrize("answers", [{}, {"k": None}, {"k": {}}, {"k": "0.9"}, {"k": [0.9]}, None])
def test_accessors_are_none_on_missing_node(answers):
    assert plane.noul(answers, "k") is None
    assert plane.choice_of(answers, "k") is None
    assert plane.score_of(answers, "k") is None


def test_noul_zero_is_a_real_answer_not_missing():
    assert plane.noul({"k": {"noul": 0}}, "k") == 0.0
    assert plane.noul({"k": {"noul": 1.0}}, "k") == 1.0


@pytest.mark.parametrize("bad", NON_FINITE + NOT_NUMBERS + (-0.01, 1.01))
def test_choice_of_is_none_on_unusable_confidence(bad):
    assert plane.choice_of({"k": {"choice": "bug", "confidence": bad}}, "k") is None


@pytest.mark.parametrize("choice", [None, "", "   ", 3, ["bug"]])
def test_choice_of_is_none_without_a_choice(choice):
    assert plane.choice_of({"k": {"choice": choice, "confidence": 0.9}}, "k") is None


def test_choice_of_returns_choice_and_confidence():
    assert plane.choice_of({"k": {"choice": "bug", "confidence": 0.9}}, "k") == ("bug", 0.9)
    assert plane.choice_of({"k": {"choice": "bug", "confidence": 0}}, "k") == ("bug", 0.0)


@pytest.mark.parametrize("bad", NON_FINITE + NOT_NUMBERS)
def test_score_of_is_none_on_unusable_input(bad):
    assert plane.score_of({"k": {"type": "score", "score": bad}}, "k") is None


def test_score_of_zero_is_a_real_answer_not_missing():
    assert plane.score_of({"k": {"score": 0}}, "k") == 0.0
    assert plane.score_of({"k": {"score": 1.85}}, "k") == 1.85


# --- compose: no label from a missing key, reader_status never OK ----------------------------

@pytest.mark.parametrize("pack_id", sorted(PACK_KEYS))
def test_all_missing_is_unavailable_with_no_label(pack_id):
    for answers in ({}, None):
        decision = plane.compose(pack_id, answers)
        assert decision["reader_status"] == "UNAVAILABLE", decision
        assert decision["labels"] == []
        assert decision["action"] not in ("label", "escalate")
        assert decision["request_info"] is True
        assert sorted(decision["unavailable"]) == sorted(PACK_KEYS[pack_id])
        for key in PACK_KEYS[pack_id]:
            assert f"{key}=UNAVAILABLE" in decision["reasons"]
        assert_advisory(decision)


@pytest.mark.parametrize("pack_id", sorted(PACK_KEYS))
@pytest.mark.parametrize("bad", NON_FINITE)
def test_all_non_finite_is_unavailable_with_no_label(pack_id, bad):
    answers = fixture_answers(FIXTURE_FOR_PACK[pack_id])
    for node in answers.values():
        for field in ("noul", "score", "confidence"):
            if field in node:
                node[field] = bad
    decision = plane.compose(pack_id, answers)
    assert decision["reader_status"] == "UNAVAILABLE", decision
    assert decision["labels"] == []
    assert decision["action"] not in ("label", "escalate")
    assert_advisory(decision)


@pytest.mark.parametrize("pack_id", sorted(PACK_KEYS))
def test_each_missing_key_degrades_and_never_reads_ok(pack_id):
    full = fixture_answers(FIXTURE_FOR_PACK[pack_id])
    baseline = plane.compose(pack_id, full)
    assert baseline["reader_status"] == "OK"
    for key in PACK_KEYS[pack_id]:
        for value in (None, float("nan")):
            answers = json.loads(json.dumps(full))
            if value is None:
                answers.pop(key)
            else:
                answers[key] = {**answers[key], **{f: value for f in ("noul", "score", "confidence")
                                                   if f in answers[key]}}
            decision = plane.compose(pack_id, answers)
            assert decision["reader_status"] == "DEGRADED", (key, decision)
            assert decision["unavailable"] == [key]
            assert f"{key}=UNAVAILABLE" in decision["reasons"]
            assert decision["request_info"] is True
            assert decision["action"] != "label"
            assert_advisory(decision)


def test_github_missing_kind_emits_no_kind_label():
    answers = fixture_answers("github_11_12.json")
    answers["kind"]["confidence"] = float("nan")
    decision = plane.compose("szl.github_item.v1", answers)
    assert "governance" in decision["labels"]  # from claim_risk, which is present
    assert decision["reader_status"] == "DEGRADED"
    answers = fixture_answers("github_11_12.json")
    answers["kind"] = {"type": "choice", "choice": "bug", "confidence": float("nan")}
    answers["claim_risk"]["noul"] = 0.01
    decision = plane.compose("szl.github_item.v1", answers)
    assert "bug" not in decision["labels"], decision


def test_github_missing_actionable_emits_no_question_label():
    answers = fixture_answers("github_11_12.json")
    del answers["actionable"]
    decision = plane.compose("szl.github_item.v1", answers)
    assert "question" not in decision["labels"]
    assert "actionable=UNAVAILABLE" in decision["reasons"]


def test_origin_missing_role_emits_no_origin_label():
    answers = fixture_answers("origin_honest_ok.json")
    del answers["surface_role"]
    decision = plane.compose("szl.origin_claim.v1", answers)
    assert not [label for label in decision["labels"] if label.startswith("origin:")]


def test_hub_missing_class_emits_no_hub_label():
    answers = fixture_answers("hub_lora_candidate.json")
    answers["artifact_class"]["confidence"] = float("inf")
    decision = plane.compose("szl.hub_card.v1", answers)
    assert not [label for label in decision["labels"] if label.startswith("hub:")]


def test_present_evidence_still_blocks_when_a_sibling_is_missing():
    answers = fixture_answers("origin_count_drift.json")
    del answers["honesty_severity"]
    decision = plane.compose("szl.origin_claim.v1", answers)
    assert decision["block_publish"] is True
    assert decision["action"] == "block_publish"
    assert decision["reader_status"] == "DEGRADED"


# --- fixtures for this slice -----------------------------------------------------------------

def test_nan_fixture_really_carries_nan():
    answers = fixture_answers("nan_github_item.json")
    numbers = [v for node in answers.values() for f, v in node.items()
               if f in ("noul", "score", "confidence")]
    assert numbers and all(math.isnan(v) for v in numbers)


def test_nan_github_item_is_not_a_clean_label():
    out = run("nan_github_item.json")
    decision = out["decision"]
    assert decision["action"] != "label", decision
    assert decision["labels"] == []
    assert decision["reader_status"] == "UNAVAILABLE"
    assert decision["request_info"] is True
    assert_advisory(decision)
    assert "NaN" not in json.dumps(decision)


def test_missing_router_intent_abstains():
    out = run("missing_router_intent.json")
    decision = out["decision"]
    assert decision["action"] == "abstain", decision
    assert decision["abstain"] is True
    assert decision["labels"] == []
    assert decision["reader_status"] == "DEGRADED"
    assert "prompt_injection=UNAVAILABLE" in decision["reasons"]
    assert_advisory(decision)


@pytest.mark.parametrize(
    "answers", [{}, None, {"handler": {"choice": "code", "confidence": float("nan")}}]
)
def test_router_abstains_on_missing_inputs(answers):
    decision = plane.compose("szl.router_intent.v1", answers)
    assert decision["action"] == "abstain", decision
    assert decision["abstain"] is True
    assert not [label for label in decision["labels"] if label.startswith("handler:")]


def test_router_present_refusal_still_wins_over_abstain():
    answers = fixture_answers("router_refuse_gates.json")
    del answers["stakes"]
    decision = plane.compose("szl.router_intent.v1", answers)
    assert decision["refuse"] is True
    assert decision["action"] == "refuse"
    assert decision["abstain"] is True


def test_router_complete_answers_do_not_abstain():
    decision = run("router_refuse_gates.json")["decision"]
    assert decision["abstain"] is False
    assert decision["reader_status"] == "OK"


def test_client_unavailable_payload_composes_to_unavailable():
    from client import unavailable

    reader = unavailable("TYPESAFE_API_KEY missing", "szl.github_item.v1")
    decision = plane.compose(reader["pack_id"], reader["answers"])
    assert decision["reader_status"] == "UNAVAILABLE"
    assert decision["labels"] == []
    assert decision["action"] != "label"


def test_cli_without_answers_is_unavailable_not_a_crash():
    proc = subprocess.run(
        [sys.executable, str(COMPOSE)],
        input=json.dumps({"pack_id": "szl.github_item.v1"}),
        text=True,
        capture_output=True,
        check=True,
    )
    decision = json.loads(proc.stdout)["decision"]
    assert decision["reader_status"] == "UNAVAILABLE"
    assert decision["labels"] == []


# --- constants -------------------------------------------------------------------------------

def test_auto_and_allow_alone_constants_stay_false():
    assert plane.AUTO_MERGE is False
    assert plane.AUTO_CLOSE is False
    assert plane.JEV_ALLOW_ALONE is False


def test_unknown_pack_fails_loudly():
    with pytest.raises(SystemExit):
        plane.compose("szl.unknown.v1", {})


def test_overclaim_live_stamp_blocks_publish():
    decision = run("overclaim_live_stamp.json")["decision"]
    assert decision["block_publish"] is True, decision
    assert decision["block_merge"] is True
    assert decision["action"] == "block_publish"
    assert decision["auto_merge"] is False
    assert decision["jev_allow_alone"] is False
    assert_advisory(decision)


def test_overclaim_measured_ok_labels_and_does_not_block():
    decision = run("overclaim_measured_ok.json")["decision"]
    assert decision["reader_status"] == "OK", decision
    assert decision["block_publish"] is False
    assert "class:MEASURED" in decision["labels"]
    assert "reader:MEASURED" in decision["labels"]
    assert decision["auto_merge"] is False
    assert_advisory(decision)


def test_overclaim_unavailable_holds_and_never_passes():
    decision = run("overclaim_unavailable.json")["decision"]
    assert decision["action"] == "hold", decision
    assert decision["block_merge"] is True
    assert decision["block_publish"] is False
    assert "never PASS" in " ".join(decision["reasons"])
    assert decision["auto_merge"] is False
    assert_advisory(decision)


def test_overclaim_cli_fixtures_do_not_systemexit():
    for name in (
        "overclaim_live_stamp.json",
        "overclaim_measured_ok.json",
        "overclaim_unavailable.json",
    ):
        out = run(name)
        assert out["decision"]["pack_id"].endswith("overclaim_reader.v1")
# --- the optional overclaim reader never acquires action authority -----------------------------

OVERCLAIM_PACK = "szl.overclaim_reader.v1"
OVERCLAIM_NOULS = PACK_KEYS[OVERCLAIM_PACK][1:-1]


def test_overclaim_live_stamp_blocks_even_with_out_of_range_severity():
    decision = run("overclaim_live_stamp.json")["decision"]
    assert decision["block_publish"] is True
    assert decision["block_merge"] is True
    assert decision["action"] == "block_publish"
    # Three criteria make the score domain [0, 2]; 2.1 is not usable evidence.
    assert "overclaim_severity" in decision["unavailable"]
    assert decision["reader_status"] == "DEGRADED"
    assert_advisory(decision)


def test_overclaim_measured_fixture_is_advisory_not_authorization():
    decision = run("overclaim_measured_ok.json")["decision"]
    assert decision["action"] == "label", decision
    assert decision["reader_status"] == "OK"
    assert decision["block_publish"] is False
    assert decision["block_merge"] is False
    assert decision["request_info"] is False
    assert_advisory(decision)


def test_overclaim_unavailable_fixture_is_held_not_an_ok_answer():
    decision = run("overclaim_unavailable.json")["decision"]
    assert decision["reader_status"] == "UNAVAILABLE", decision
    assert decision["request_info"] is True
    assert decision["block_merge"] is True
    assert decision["action"] != "label"
    assert decision["labels"] == []
    assert_advisory(decision)


@pytest.mark.parametrize("choice", ["LIVE", "PASS", "UNKNOWN", "measured", " MEASURED ", 0, True])
def test_overclaim_unknown_or_untyped_choice_never_gets_clean_label(choice):
    answers = fixture_answers("overclaim_measured_ok.json")
    answers["evidence_class"]["choice"] = choice
    decision = plane.compose(OVERCLAIM_PACK, answers)
    assert "evidence_class" in decision["unavailable"]
    assert decision["reader_status"] != "OK"
    assert decision["action"] != "label"
    assert not [label for label in decision["labels"] if "MEASURED" in label or "LIVE" in label]
    assert decision["request_info"] is True
    assert_advisory(decision)


@pytest.mark.parametrize("key", PACK_KEYS[OVERCLAIM_PACK])
@pytest.mark.parametrize("wrong_type", [None, "wrong", True, 1, {}, []])
def test_overclaim_mismatched_node_type_is_unavailable(key, wrong_type):
    answers = fixture_answers("overclaim_measured_ok.json")
    if wrong_type is None:
        del answers[key]["type"]
    else:
        answers[key]["type"] = wrong_type
    decision = plane.compose(OVERCLAIM_PACK, answers)
    assert key in decision["unavailable"], (key, wrong_type, decision)
    assert decision["reader_status"] != "OK"
    assert decision["action"] != "label"
    assert decision["request_info"] is True
    assert_advisory(decision)


@pytest.mark.parametrize("bad", NON_FINITE + NOT_NUMBERS + (-0.01, 1.01))
@pytest.mark.parametrize("key", OVERCLAIM_NOULS)
def test_overclaim_noul_unusable_values_do_not_become_zero(key, bad):
    answers = fixture_answers("overclaim_measured_ok.json")
    answers[key]["noul"] = bad
    decision = plane.compose(OVERCLAIM_PACK, answers)
    assert key in decision["unavailable"]
    assert decision["reader_status"] != "OK"
    assert decision["action"] != "label"
    assert decision["request_info"] is True
    assert_advisory(decision)


@pytest.mark.parametrize("bad", NON_FINITE + NOT_NUMBERS + (-0.01, 2.01))
def test_overclaim_score_is_bounded_to_three_criteria(bad):
    answers = fixture_answers("overclaim_measured_ok.json")
    answers["overclaim_severity"]["score"] = bad
    decision = plane.compose(OVERCLAIM_PACK, answers)
    assert "overclaim_severity" in decision["unavailable"]
    assert decision["reader_status"] != "OK"
    assert decision["action"] != "label"
    assert_advisory(decision)


@pytest.mark.parametrize("key", OVERCLAIM_NOULS)
def test_overclaim_present_risk_still_blocks_when_class_unavailable(key):
    answers = fixture_answers("overclaim_measured_ok.json")
    answers["evidence_class"]["choice"] = "UNAVAILABLE"
    answers[key]["noul"] = 0.91
    decision = plane.compose(OVERCLAIM_PACK, answers)
    assert decision["block_publish"] is True, decision
    assert decision["block_merge"] is True
    assert decision["action"] == "block_publish"
    assert decision["request_info"] is True
    assert_advisory(decision)


def test_overclaim_present_score_still_blocks_when_class_missing():
    answers = fixture_answers("overclaim_measured_ok.json")
    del answers["evidence_class"]
    answers["overclaim_severity"]["score"] = 2
    decision = plane.compose(OVERCLAIM_PACK, answers)
    assert decision["block_publish"] is True
    assert decision["block_merge"] is True
    assert decision["action"] == "block_publish"
    assert decision["reader_status"] == "DEGRADED"
    assert_advisory(decision)


def test_overclaim_measured_choice_cannot_hide_a_missing_sibling():
    answers = fixture_answers("overclaim_measured_ok.json")
    del answers["unsigned_as_live"]
    decision = plane.compose(OVERCLAIM_PACK, answers)
    assert decision["reader_status"] == "DEGRADED"
    assert decision["block_merge"] is True
    assert decision["action"] != "label"
    assert not [label for label in decision["labels"] if "MEASURED" in label]
    assert_advisory(decision)


@pytest.mark.parametrize("choice,confidence", [("HOLD", 0.91), ("MEASURED", 0.54)])
def test_overclaim_hold_or_low_confidence_cannot_label_measured(choice, confidence):
    answers = fixture_answers("overclaim_measured_ok.json")
    answers["evidence_class"].update(choice=choice, confidence=confidence)
    decision = plane.compose(OVERCLAIM_PACK, answers)
    assert decision["block_merge"] is True
    assert decision["action"] == "hold"
    assert not [label for label in decision["labels"] if "MEASURED" in label]
    assert_advisory(decision)


def test_overclaim_unavailable_choice_with_complete_nodes_never_reports_ok():
    answers = fixture_answers("overclaim_measured_ok.json")
    answers["evidence_class"].update(choice="UNAVAILABLE", confidence=0.91)
    decision = plane.compose(OVERCLAIM_PACK, answers)
    assert decision["reader_status"] != "OK"
    assert decision["request_info"] is True
    assert decision["block_merge"] is True
    assert decision["action"] != "label"
    assert_advisory(decision)
