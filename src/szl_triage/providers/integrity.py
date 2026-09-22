"""Integrity providers.

The integrity axis is the veto input to Lambda. Zero-pinning means a provider can only
ever fail closed: a low score forces lambda to 0.0 and the verdict to REVIEW, while a high
score can never rescue an axis that is already zero. That property is what makes it safe to
let a model influence this axis at all.

Contract, deliberately narrow:
  score(text) -> (value in [0.0, 1.0], span or None, provenance str)

A provider returns a score and, when it lowers the score, a span that must occur literally
in the input. The caller verifies the span before the score is honoured. A provider never
returns a label.
"""
from __future__ import annotations

from typing import Optional, Protocol, Tuple


class IntegrityProvider(Protocol):
    name: str
    provenance: str

    def score(self, text: str) -> Tuple[float, Optional[str], str]:
        ...


class NullIntegrityProvider:
    """Returns 1.0 always - byte-identical to the engine's behaviour before the seam
    existed. Its purpose is to prove the seam is behaviour-preserving, so any later change
    in the scoreboard is attributable to a real provider and not to the plumbing."""

    name = "null"
    provenance = "NULL_PROVIDER_NO_JUDGEMENT"

    def score(self, text: str) -> Tuple[float, Optional[str], str]:
        return 1.0, None, self.provenance


def apply_provider(text: str, base_integrity: float, provider: IntegrityProvider) -> dict:
    """Combine a provider's score with the engine's own integrity value.

    Rules, in order:
      1. the provider may only LOWER integrity, never raise it - min() is taken
      2. a lowered score must be justified by a span that literally occurs in the text
      3. an unjustified lowering is discarded and recorded, not silently applied
    """
    value, span, prov = provider.score(text)
    if not (0.0 <= value <= 1.0):
        return {"integrity": base_integrity, "applied": False,
                "reason": "provider returned out-of-range value", "provider": provider.name}
    if value >= base_integrity:
        return {"integrity": base_integrity, "applied": False,
                "reason": "provider did not lower integrity", "provider": provider.name,
                "provenance": prov}
    if span is not None and span not in text:
        return {"integrity": base_integrity, "applied": False,
                "reason": "span not found in input - lowering discarded", "provider": provider.name,
                "span": span}
    return {"integrity": min(base_integrity, value), "applied": True, "span": span,
            "provider": provider.name, "provenance": prov}