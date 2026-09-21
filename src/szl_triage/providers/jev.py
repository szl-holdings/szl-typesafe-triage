"""Jev backend for the System One integrity question.

API shape per TypeSafe's published guide: typesafe-sdk, TypeSafeClient().system_one(
state=..., questions={name: Noul(instructions=...)}), answer.noul is a probability in [0,1].
Model is pinned rather than jev-latest, because jev-latest moves and would silently change
answers under a tuned threshold.

Doctrine conflicts recorded rather than hidden:
  1. Jev is hosted. Calling it sends the ticket text off this machine. That is incompatible
     with the air-gapped posture the rest of the estate claims, so this backend is a
     comparison arm and never a production dependency.
  2. TypeSafe's jaggedness page states that state is not treated as hostile and that
     adversarially engineered text can move the answer - "that is your threat model to
     handle. Test it." The steering family IS adversarially engineered text, so this is
     precisely the case they disclaim.
  3. Jev's zero-structured-error figure is asserted by construction, not measured, and its
     benchmark column measures agreement with two frontier models rather than accuracy.
"""
from __future__ import annotations

import os
from typing import Optional

from .systemone import DIRECTIVE_NOUL, answer_receipt

PINNED_MODEL = "jev-1.13.0"


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
        """Returns an answer receipt. When the backend is unavailable the value is None and
        the reason is recorded - never a substituted number."""
        if self.unavailable or self.client is None:
            r = answer_receipt(question, None, self.id, state, self.provenance)
            r["unavailable"] = self.unavailable
            r["state_left_host"] = False
            return r
        try:
            from typesafe_sdk import Noul  # type: ignore
            resp = self.client.system_one(
                state=state,
                questions={question.id: Noul(instructions=question.statement)})
            ans = resp.answers[question.id]
            value = float(ans.noul)
            r = answer_receipt(question, value, self.id, state, self.provenance)
            r["model_reported"] = getattr(resp, "model", None)
            r["model_pinned"] = self.model
            r["state_left_host"] = True
            r["determinism"] = "UNVERIFIED - repeat the call to check reproducibility before tuning a threshold"
            return r
        except Exception as exc:
            r = answer_receipt(question, None, self.id, state, self.provenance)
            r["unavailable"] = "call failed: " + type(exc).__name__ + ": " + str(exc)[:200]
            r["state_left_host"] = True
            return r