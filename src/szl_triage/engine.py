# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Tier 2: the deterministic engine.

Weighted keyword evidence, normalized per policy, gated on an absolute
confidence floor and a margin over the runner-up. Same input and same policy
always yield the same decision -- no sampling, no temperature, no network.

The engine is cheap and handles the in-lexicon majority. Its ceiling is its
lexicon: an input that shares no vocabulary with the policy scores zero and
falls to REVIEW. That ceiling is the reason a model tier exists.
"""
from __future__ import annotations

from .contracts import Decision, State, Tier, new_decision_id, sha256_text
from .evidence import normalize
from .policy import Policy

MAX_HITS_COUNTED = 2


def score(text: str, policy: Policy) -> tuple[dict[str, float], list[str], list[str]]:
    """Score every classifiable label.

    Returns (scores, rationale, matched_terms). Repeated hits are counted at
    most twice: a word appearing ten times is not five times the evidence.
    """
    haystack = normalize(text)
    scores: dict[str, float] = {}
    rationale: list[str] = []
    matched: list[str] = []

    for label in policy.classifiable:
        base = policy.denominator(label)
        total = 0.0
        for term, weight in policy.rules[label]:
            hits = haystack.count(normalize(term))
            if hits:
                counted = min(hits, MAX_HITS_COUNTED)
                total += weight * counted
                rationale.append(f"{label}: matched {term!r} x{hits}")
                matched.append(term)
        scores[label] = round(min(total / base, 1.0), 4)

    return scores, rationale, matched


def classify(text: str, policy: Policy) -> Decision:
    """Deterministic disposition. Falls closed to REVIEW."""
    scores, rationale, matched = score(text, policy)
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    leader, top = ranked[0] if ranked else ("REVIEW", 0.0)
    runner_up = ranked[1][1] if len(ranked) > 1 else 0.0

    clears_floor = top >= policy.min_confidence
    clears_margin = (top - runner_up) >= policy.min_margin

    if clears_floor and clears_margin:
        label, state = leader, State.MEASURED
    else:
        label, state = "REVIEW", State.REVIEW
        rationale.append(
            f"below gate: confidence {top:.4f} floor {policy.min_confidence} "
            f"margin {top - runner_up:.4f} required {policy.min_margin}"
        )

    evidence = tuple(
        term
        for term in matched
        if label != "REVIEW" and term in dict(policy.rules.get(label, ()))
    )

    return Decision(
        decision_id=new_decision_id(text),
        label=label,
        state=state,
        tier=Tier.ENGINE,
        evidence=evidence,
        rationale=tuple(rationale),
        policy_name=policy.name,
        policy_version=policy.version,
        input_sha256=sha256_text(text),
        scores=scores,
    )
