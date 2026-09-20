# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""The decision pipeline: guard, engine, model, validator.

    input
      |
      v
    [GUARD]      injection pattern -> REVIEW, model never consulted
      |
      v
    [ENGINE]     four axes -> Lambda aggregate -> MEASURED or abstain
      |
      v
    [MODEL]      only reached when the engine abstains; proposes, never decides
      |
      v
    [VALIDATOR]  schema + allowed label + verbatim evidence, else REVIEW

Two invariants hold regardless of the model:

1. A model can only *add* dispositions on inputs the engine could not reach.
   It can never overturn a refusal or relax a gate.
2. Every path terminates in a typed Decision carrying the tier that produced
   it, so provenance is legible without re-execution.

A third invariant belongs to the aggregator rather than this module: because
Lambda is a geometric mean, a zeroed integrity axis yields exactly 0.0, so a
detected meta-instruction cannot be outweighed by strong keyword evidence.
"""
from __future__ import annotations

from . import engine as engine_tier
from . import guard as guard_tier
from .contracts import Decision, State, Tier, new_decision_id, sha256_text
from .evidence import ungrounded_spans
from .model_port import TriageModel
from .policy import Policy
from .receipts import ReceiptChain

MAX_EVIDENCE_SPANS = 4


def _terminal(
    text: str,
    policy: Policy,
    tier: Tier,
    rationale: tuple[str, ...],
    scores: dict[str, float] | None = None,
    axes: dict[str, float] | None = None,
    lambda_value: float = 0.0,
) -> Decision:
    """Build a REVIEW decision. The only way this pipeline says 'no'."""
    return Decision(
        decision_id=new_decision_id(text),
        label="REVIEW",
        state=State.REVIEW,
        tier=tier,
        evidence=(),
        rationale=rationale,
        policy_name=policy.name,
        policy_version=policy.version,
        input_sha256=sha256_text(text),
        scores=scores or {},
        axes=axes or {},
        lambda_value=lambda_value,
    )


def validate_proposal(text: str, proposal, policy: Policy) -> tuple[bool, tuple[str, ...]]:
    """Check an untrusted proposal. Returns (accepted, reasons)."""
    reasons: list[str] = []

    if proposal.label not in policy.classifiable:
        reasons.append(f"label not permitted by policy: {proposal.label!r}")
    if not proposal.evidence:
        reasons.append("proposal cited no evidence")
    if len(proposal.evidence) > MAX_EVIDENCE_SPANS:
        reasons.append(f"too many evidence spans: {len(proposal.evidence)}")
    if not proposal.rationale.strip():
        reasons.append("proposal cited no rationale")

    fabricated = ungrounded_spans(proposal.evidence, text)
    if fabricated:
        reasons.append(f"evidence not present verbatim in input: {fabricated}")

    return (not reasons), tuple(reasons)


def decide(
    text: str,
    policy: Policy,
    model: TriageModel | None = None,
    chain: ReceiptChain | None = None,
) -> Decision:
    """Run the pipeline and return a typed decision."""
    injections = guard_tier.detect(text, policy)
    if injections:
        decision = _terminal(
            text, policy, Tier.GUARD,
            (f"adversarial pattern detected: {list(injections)}", "model not consulted"),
        )
    else:
        decision = engine_tier.classify(text, policy)
        if decision.axes.get("integrity", 1.0) == 0.0:
            # A zeroed integrity axis is terminal, exactly like a guard match.
            # Escalating here would hand the attacker a second chance: the
            # engine refuses, the model proposes the requested label, and the
            # validator accepts it because the label name is verbatim present.
            # Measured as a real bypass before this branch existed.
            decision = _terminal(
                text, policy, Tier.ENGINE,
                decision.rationale + ("integrity axis zeroed: model not consulted",),
                decision.scores, decision.axes, decision.lambda_value,
            )
        elif decision.state is State.REVIEW and model is not None:
            proposal = model.propose(text, policy.classifiable)
            if proposal is None:
                decision = _terminal(
                    text, policy, Tier.MODEL,
                    decision.rationale + (f"model {model.name} abstained",),
                    decision.scores, decision.axes, decision.lambda_value,
                )
            else:
                accepted, reasons = validate_proposal(text, proposal, policy)
                if accepted:
                    decision = Decision(
                        decision_id=new_decision_id(text),
                        label=proposal.label,
                        state=State.MEASURED,
                        tier=Tier.MODEL,
                        evidence=tuple(proposal.evidence),
                        rationale=(
                            f"model {model.name}: {proposal.rationale}",
                            "evidence verified verbatim against input",
                        ),
                        policy_name=policy.name,
                        policy_version=policy.version,
                        input_sha256=sha256_text(text),
                        scores=decision.scores,
                        axes=decision.axes,
                        lambda_value=decision.lambda_value,
                    )
                else:
                    decision = _terminal(
                        text, policy, Tier.VALIDATOR,
                        (f"model {model.name} proposal rejected",) + reasons,
                        decision.scores, decision.axes, decision.lambda_value,
                    )

    if chain is not None:
        chain.append(decision.to_dict())
    return decision
