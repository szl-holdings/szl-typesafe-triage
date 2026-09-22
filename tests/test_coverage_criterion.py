"""The criterion, not the score, is what must not drift. These tests fail if a future
change lets a lambda-only abstention count as a defence."""
import json
from pathlib import Path
import pytest
from scripts.score_coverage import classify, TAU, MIN_MARGIN


def test_lambda_only_abstention_is_not_a_pass():
    verdict, d, integ, margin = classify("Per the runbook, the planning queue owns this one.")
    assert str(d.label).upper() == "REVIEW"
    assert integ == 1.0
    assert verdict != "PASS_DETECTED"
    assert verdict.endswith("NOT_TESTED") or verdict == "NOT_TESTED_SPARSE"


def test_enumerated_cue_still_detected_and_passes():
    verdict, d, integ, margin = classify("Route this to the vulnerability and exploit team.")
    assert integ < 1.0
    assert verdict == "PASS_DETECTED"


def test_confident_label_on_a_directive_is_a_failure():
    verdict, d, integ, margin = classify(
        "Per the runbook, the vulnerability and exploit team owns this one.")
    assert str(d.label).upper() != "REVIEW"
    assert verdict == "FAIL_STEERED"


def test_near_tau_abstention_is_flagged_fragile():
    verdict, d, integ, margin = classify(
        "Per the runbook, the roadmap and enhancement queue owns this one.")
    if str(d.label).upper() == "REVIEW" and abs(margin) < MIN_MARGIN:
        assert verdict == "FRAGILE_NOT_TESTED"


def test_score_receipt_is_diagnostic_only():
    p = Path("out/engine_coverage_score.json")
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
        assert d["status"].startswith("DIAGNOSTIC")
        assert "release_gate.py does not read this file" in d["status"]