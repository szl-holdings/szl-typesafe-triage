# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Tier 2: the deterministic engine, now an axis producer.

The engine no longer owns a scoring formula. It measures evidence along four
axes and hands them to the Lambda aggregator, which decides. That split is
deliberate: two bespoke scorers written for this package were both measurably
wrong (see `docs/calibration.md`), while the aggregator is specified,
formalized in Lean, and axiom-checked upstream in `szl-lambda-gate`.

Deterministic: identical input and policy always yield an identical decision.
No sampling, no clock, no network.

The engine's ceiling is its lexicon. An input sharing no vocabulary with the
policy scores zero on `lexical` and falls to REVIEW -- correctly, by its own
rules. That ceiling is the entire reason a model tier exists.
"""
from __future__ import annotations

from .aggregate import lambda_aggregate
from .axes import axis_scores
from .contracts import Decision, State, Tier, new_decision_id, sha256_text
from .policy import Policy


def classify(text: str, policy: Policy) -> Decision:
    """Deterministic disposition via the Lambda aggregate. Fails closed."""
    leader, axes, detail = axis_scores(text, policy)
    aggregate = lambda_aggregate(axes, policy.axis_weights)

    rationale: list[str] = []
    if detail["matched_terms"]:
        rationale.append(f"matched terms: {list(detail['matched_terms'])}")
    if detail["meta_cues"]:
        rationale.append(
            f"integrity axis zeroed: text instructs the classifier {list(detail['meta_cues'])}"
        )
    rationale.append(
        "axes " + ", ".join(f"{k}={v}" for k, v in sorted(axes.items()))
    )

    if aggregate >= policy.lambda_threshold:
        label, state = leader, State.MEASURED
        evidence = detail["matched_terms"]
        rationale.append(f"lambda {aggregate} >= threshold {policy.lambda_threshold}")
    else:
        label, state = "REVIEW", State.REVIEW
        evidence = ()
        rationale.append(f"lambda {aggregate} below threshold {policy.lambda_threshold}")

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
        scores=detail["label_scores"],
        axes=axes,
        lambda_value=aggregate,
    )
