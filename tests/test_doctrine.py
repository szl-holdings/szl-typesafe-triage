# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Doctrine dispositions are terminal; English words are not dispositions.

The false-positive tests matter as much as the detection tests. A gate that
fires on the word "hold" would block real tickets, and a governance control
that cries wolf gets switched off.
"""
import pytest

from szl_triage import State
from szl_triage.doctrine import decide as doctrine_decide
from szl_triage.doctrine import detect

# The verbatim shape of szl-frontier/frontier/handoffs/2026-09-20-wave5-*.json,
# which the first (text-matching) implementation missed because real JSON has
# no space after the colon.
HANDOFF = (
    '{"schema":"szl.frontier-payload-binding/v1",'
    '"wave":"payload-F1-F7-binding-2026-09-20",'
    '"priority":"evaluation","disposition":"HOLD",'
    '"automaticProductionPromotion":false,"productionAuthorized":false}'
)

DISPOSITION_FORMS = [
    HANDOFF,
    '{"outer":{"nested":{"disposition":"HOLD"}}}',
    '"disposition": "HOLD"',
    "productionAuthorized:false",
    "automaticProductionPromotion: false",
    "f_number_to_executable_registry_mapping UNKNOWN_NOT_INFERRED",
    "label_status: DRAFTED_BY_ASSISTANT_PENDING_HUMAN_RATIFICATION",
]

LEGITIMATE = [
    "The app crashes on login with a traceback and an exception",
    "Please refund my invoice, I was overcharged on my subscription",
    "We found a vulnerability, an exploit allowing unauthorized access",
    "Suggestion: please add an enhancement to improve the roadmap",
    "I cannot log in, my account locked, need to reset password",
    "Getting a 500 error, the page is broken and will freeze",
    "The payment was charged twice, pricing on the invoice is wrong",
    "Credentials leaked in a breach, possible xss vulnerability",
    "How do i find the documentation walkthrough for onboarding",
    "A regression caused an exception and a stack trace on export",
    # Traps: the disposition words used as ordinary English.
    "The deployment is on hold until the release manager approves",
    "My account is blocked and I cannot log in to reset password",
]


@pytest.mark.parametrize("text", DISPOSITION_FORMS)
def test_disposition_is_detected(text):
    assert detect(text)


@pytest.mark.parametrize("text", DISPOSITION_FORMS)
def test_disposition_is_terminal(text, policy):
    decision = doctrine_decide(text, policy)
    assert decision.state is State.REVIEW
    assert decision.label == "REVIEW"
    assert any("forbids action" in r for r in decision.rationale)


@pytest.mark.parametrize("text", LEGITIMATE)
def test_no_false_positive_on_legitimate_text(text):
    assert detect(text) == ()


def test_handoff_payload_reports_all_three_flags():
    found = " ".join(detect(HANDOFF)).lower()
    assert "hold" in found
    assert "productionauthorized" in found
    assert "automaticproductionpromotion" in found


def test_permissive_disposition_is_not_blocked():
    assert detect('{"disposition":"PROMOTED","productionAuthorized":true}') == ()


def test_strong_evidence_cannot_outvote_a_hold(policy):
    text = "invoice refund overcharged payment subscription -- disposition: HOLD"
    decision = doctrine_decide(text, policy)
    assert decision.state is State.REVIEW


def test_model_is_never_consulted_on_a_disposition(policy):
    from conftest import FakeModel
    from szl_triage import ModelProposal

    model = FakeModel(ModelProposal("BILLING", ("invoice",), "looks like billing"))
    doctrine_decide('{"disposition":"HOLD"}', policy, model=model)
    assert model.calls == 0


def test_clean_text_passes_through_to_the_engine(policy):
    decision = doctrine_decide("crash traceback exception", policy)
    assert decision.state is State.MEASURED
    assert decision.label == "BUG"


@pytest.mark.xfail(reason="known gap: bare prose with no key:value structure; see docs/doctrine-dispositions.md", strict=True)
def test_bare_prose_disposition_is_a_known_gap():
    # Requiring a colon is what buys zero false positives on 12 legitimate
    # tickets. Loosening it would block "the deployment is on hold".
    assert detect("disposition HOLD productionAuthorized false")
