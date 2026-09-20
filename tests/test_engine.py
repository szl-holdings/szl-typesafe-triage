# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""The engine is an axis producer; Lambda decides. Determinism is a contract."""
from szl_triage import State, Tier
from szl_triage.engine import classify


def test_strong_bug_is_measured(policy):
    decision = classify("The app crashes on login with a traceback and an exception", policy)
    assert decision.state is State.MEASURED and decision.label == "BUG"


def test_strong_billing_is_measured(policy):
    decision = classify("Please refund the invoice, I was overcharged", policy)
    assert decision.state is State.MEASURED and decision.label == "BILLING"


def test_tier_is_always_engine(policy):
    assert classify("crash traceback exception", policy).tier is Tier.ENGINE


def test_single_keyword_abstains(policy):
    assert classify("crash", policy).state is State.REVIEW


def test_no_vocabulary_overlap_abstains(policy):
    # The engine's ceiling is its lexicon. This is the reason a model tier exists.
    assert classify("quarterly synergy alignment offsite", policy).state is State.REVIEW


def test_abstention_carries_no_evidence(policy):
    assert classify("crash", policy).evidence == ()


def test_decision_records_axes_and_lambda(policy):
    decision = classify("crash traceback exception", policy)
    assert set(decision.axes) == {"lexical", "breadth", "integrity", "separation"}
    assert decision.lambda_value > 0


def test_rationale_explains_threshold_comparison(policy):
    assert any("threshold" in r for r in classify("crash", policy).rationale)


def test_deterministic_across_calls(policy):
    first = classify("invoice refund overcharged", policy)
    second = classify("invoice refund overcharged", policy)
    assert first.to_json() == second.to_json()


def test_input_hash_is_recorded(policy):
    assert len(classify("crash", policy).input_sha256) == 64
