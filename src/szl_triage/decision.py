"""One decision record, one source of truth.

RefusalPath:   PRE_AGGREGATION | ZERO_PINNED | BELOW_THRESHOLD | NONE
refusal_reason (PRE_AGGREGATION only): INJECTION_GUARD | META_CUE | UNIDENTIFIED

INJECTION_GUARD is decide()'s guard_tier.detect firing on policy.injection_phrases before any
axis exists; the model is not consulted. META_CUE is an enumerated handling cue. UNIDENTIFIED
remains for a refusal no known guard explains - it is now expected to be empty.

UNIDENTIFIED is used where the engine refuses before computing axes and no enumerated
meta_cue explains it. Naming a mechanism that has not been located in the code would be a
guess wearing a label.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence

PRE_AGGREGATION = "PRE_AGGREGATION"
ZERO_PINNED = "ZERO_PINNED"
BELOW_THRESHOLD = "BELOW_THRESHOLD"
NONE = "NONE"
PATHS = (PRE_AGGREGATION, ZERO_PINNED, BELOW_THRESHOLD, NONE)
META_CUE = "META_CUE"
INJECTION_GUARD = "INJECTION_GUARD"
UNIDENTIFIED = "UNIDENTIFIED"
REASONS = (META_CUE, INJECTION_GUARD, UNIDENTIFIED, None)


class AxesUnavailable(KeyError):
    """Substituting zeros for missing axes manufactures the condition the aggregator treats
    as a veto. This raises instead."""


@dataclass(frozen=True)
class DecisionRecord:
    input_digest: str
    label: str
    state: str
    lambda_value: float
    threshold: float
    axes: Mapping[str, float] = field(default_factory=dict)
    refusal_path: str = NONE
    refusal_reason: Optional[str] = None
    aggregated: bool = True
    provider: Optional[str] = None
    provider_applied: bool = False
    provenance: str = "ENGINE_DETERMINISTIC"

    @property
    def confident(self) -> bool:
        return self.refusal_path == NONE

    def axes_vector(self, order: Sequence[str]) -> list:
        if not self.aggregated:
            raise AxesUnavailable("refused via " + self.refusal_path + "/" + str(self.refusal_reason))
        missing = [k for k in order if k not in self.axes]
        if missing:
            raise AxesUnavailable("axes missing and will not be defaulted: " + ", ".join(missing))
        return [float(self.axes[k]) for k in order]


def digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def classify(text: str, policy, provider=None) -> DecisionRecord:
    from .axes import normalize
    from .pipeline import decide
    from .providers.integrity import apply_provider

    tau = float(policy.lambda_threshold)
    weights = dict(policy.axis_weights)
    d = decide(text, policy)
    axes = {k: float(v) for k, v in dict(d.axes).items()}
    label, state, lam = str(d.label).upper(), str(d.state).upper(), float(d.lambda_value)

    if set(axes) != set(weights):
        hay = normalize(text)
        phrases = tuple(getattr(policy, "injection_phrases", ()) or ())
        if any(normalize(x) in hay for x in phrases):
            reason = INJECTION_GUARD
        elif any(normalize(c) in hay for c in policy.meta_cues):
            reason = META_CUE
        else:
            reason = UNIDENTIFIED
        return DecisionRecord(digest(text), label, state, lam, tau, dict(axes),
                              PRE_AGGREGATION, reason, aggregated=False)

    applied, prov_name = False, None
    if provider is not None:
        prov_name = getattr(provider, "name", getattr(provider, "id", "provider"))
        res = apply_provider(text, axes.get("integrity", 1.0), provider)
        applied = bool(res.get("applied"))
        if applied:
            axes = dict(axes)
            axes["integrity"] = float(res["integrity"])
            p = 1.0
            for k, w in weights.items():
                v = axes[k]
                if v <= 0.0:
                    p = 0.0
                    break
                p *= v ** w
            lam = round(p, 4)
            if lam < tau:
                label, state = "REVIEW", "REVIEW"

    path = ZERO_PINNED if any(v == 0.0 for v in axes.values()) else (
        BELOW_THRESHOLD if lam < tau else NONE)
    return DecisionRecord(digest(text), label, state, lam, tau, axes, path, None, True,
                          prov_name, applied,
                          "MODEL_PROPOSED_UNRATIFIED" if applied else "ENGINE_DETERMINISTIC")


def to_receipt_payload(rec: DecisionRecord, policy_id: str, kernel_commit: str, seq: int = 0) -> dict:
    return {"schema": "szl.pcgi.receipt/v1", "kind": "governance.decision",
            "producer": "szl-typesafe-triage", "policy_id": policy_id,
            "kernel_commit": kernel_commit, "seq": seq,
            "input_digest": rec.input_digest, "verdict": rec.label, "state": rec.state,
            "refusal_path": rec.refusal_path, "refusal_reason": rec.refusal_reason,
            "aggregated": rec.aggregated,
            "lambda": {"value": rec.lambda_value, "floor": rec.threshold, "pass": rec.confident,
                       "axes": len(rec.axes) or None, "uniqueness": "Conjecture 1"},
            "provider": rec.provider, "provider_applied": rec.provider_applied,
            "provenance": rec.provenance, "energy": {"joules": None, "measured": False}}