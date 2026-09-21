"""Jev backend for the System One integrity question.

API shape per TypeSafe's published guide: typesafe-sdk, TypeSafeClient().system_one(
state=..., questions={name: Noul(instructions=...)}), answer.noul is a probability in [0,1].
The model is pinned rather than jev-latest, because jev-latest moves and would silently change
answers under a tuned threshold.

Secrets never reach a receipt. Error strings are redacted before they are recorded, because an
SDK exception can carry an authenticated URL or a key fragment and this module's output is
committed to git.

Doctrine conflicts recorded rather than hidden:
  1. Jev is hosted. Calling it sends ticket text off this machine, which is incompatible with
     the air-gapped posture the estate claims. Comparison arm, never a dependency.
  2. TypeSafe's jaggedness page states state is not treated as hostile, that adversarially
     engineered text can move the answer, and that this is the caller's threat model to test.
     The steering family is exactly that case.
  3. The zero-structured-error figure is asserted by construction, not measured, and the
     benchmark column measures agreement with two frontier models rather than accuracy.
"""
from __future__ import annotations

import os
import re
from typing import Optional

from .systemone import DIRECTIVE_NOUL, answer_receipt

PINNED_MODEL = "jev-1.13.0"

_SECRET_SHAPES = (
    re.compile(r"apikey_[A-Za-z0-9]{8,}", re.I),
    re.compile(r"\b[0-9a-f]{32,}\b", re.I),
    re.compile(r"(?i)(authorization|bearer|api[-_ ]?key)\s*[:=]\s*\S+"),
)


def redact(text: str, limit: int = 200) -> str:
    """Strip secret-shaped substrings from anything destined for a receipt."""
    out = str(text)
    for pat in _SECRET_SHAPES:
        out = pat.sub("[REDACTED]", out)
    key = os.environ.get("TYPESAFE_API_KEY")
    if key and len(key) >= 8:
        out = out.replace(key, "[REDACTED]")
    return out[:limit]


class JevNoulBackend:
    id = "jev"
    provenance = "MODEL_PROPOSED_UNRATIFIED"

    def __init__(self, model: str = PINNED_MODEL):
        self.model = model
        self.client = None
        self.unavailable: Optional[str] = None
        if not os.environ.get("TYPESAFE_API_KEY"):
            self.unavailable = "TYPESAFE_API_KEY not set"
            return
        try:
            from typesafe_sdk import TypeSafeClient  # type: ignore
        except Exception as exc:
            self.unavailable = "typesafe-sdk not importable: " + type(exc).__name__
            return
        try:
            self.client = TypeSafeClient(model=model)
        except Exception as exc:
            self.unavailable = "client construction failed: " + type(exc).__name__

    def ask(self, state: str, question=DIRECTIVE_NOUL) -> dict:
        if self.unavailable or self.client is None:
            r = answer_receipt(question, None, self.id, state, self.provenance)
            r["unavailable"] = redact(self.unavailable or "client unavailable")
            r["state_left_host"] = False
            return r
        try:
            from typesafe_sdk import Noul  # type: ignore
            resp = self.client.system_one(
                state=state,
                questions={question.id: Noul(instructions=question.statement)})
            ans = resp.answers[question.id]
            r = answer_receipt(question, float(ans.noul), self.id, state, self.provenance)
            r["model_reported"] = redact(str(getattr(resp, "model", "")), 64) or None
            r["model_pinned"] = self.model
            r["state_left_host"] = True
            r["determinism"] = "UNVERIFIED - rerun and diff before tuning any threshold"
            return r
        except Exception as exc:
            r = answer_receipt(question, None, self.id, state, self.provenance)
            r["unavailable"] = "call failed: " + type(exc).__name__ + ": " + redact(exc)
            r["state_left_host"] = True
            return r