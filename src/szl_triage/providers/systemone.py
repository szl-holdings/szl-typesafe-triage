"""System One question primitives, local and receipted.

Learned from TypeSafe AI's Jev: instead of asking a model for prose and parsing it, you
declare the answer space up front and receive typed values with calibrated probabilities.
Jev's primitives are Choice, Score and Noul. This module defines the same three shapes as a
local contract so any backend - a hosted System One API, a local GGUF, or a deterministic
kernel - answers through one typed interface.

What this adds that a hosted API does not give you: every answer carries a receipt (question
id, state digest, backend id, provenance), and probabilities are claims that can be measured
against szl-calibration rather than trusted.

Not affiliated with or endorsed by TypeSafe AI. The primitive names describe the shapes.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Optional, Sequence


@dataclass(frozen=True)
class Noul:
    """Is this statement true? Returns a probability in [0,1]."""
    id: str
    statement: str
    kind: str = "noul"


@dataclass(frozen=True)
class Choice:
    """Pick exactly one of the declared options. Nothing outside options is representable."""
    id: str
    question: str
    options: Sequence[str] = field(default_factory=tuple)
    kind: str = "choice"


@dataclass(frozen=True)
class Score:
    """Rate against described levels. Returns a value in [0,1]."""
    id: str
    question: str
    levels: Sequence[str] = field(default_factory=tuple)
    kind: str = "score"


def state_digest(state: str) -> str:
    return "sha256:" + hashlib.sha256(state.encode("utf-8")).hexdigest()


def validate_answer(question, value) -> Optional[str]:
    """Return an error string if the answer escapes the declared schema, else None.
    A System One contract is only worth having if violations are impossible to ignore."""
    if question.kind in ("noul", "score"):
        if not isinstance(value, (int, float)):
            return "expected a number"
        if not (0.0 <= float(value) <= 1.0):
            return "probability outside [0,1]"
        return None
    if question.kind == "choice":
        if value not in question.options:
            return "value not among declared options"
        return None
    return "unknown question kind"


def answer_receipt(question, value, backend: str, state: str, provenance: str) -> dict:
    err = validate_answer(question, value)
    return {"schema": "szl.systemone.answer/v1",
            "question_id": question.id, "question_kind": question.kind,
            "state_digest": state_digest(state),
            "value": None if err else value,
            "schema_violation": err,
            "backend": backend, "provenance": provenance,
            "calibration": "UNVERIFIED - a probability is a claim until szl-calibration measures it",
            "signed": False}


# The directive question. This is the integrity axis expressed as a typed primitive rather
# than as an enumerated cue list.
DIRECTIVE_NOUL = Noul(
    id="handling_directive",
    statement=("This text instructs the classifier how to handle the item - naming a destination, owner or "
               "routing - rather than describing an incident, symptom or observation."))


class DeterministicBaselineBackend:
    """Answers DIRECTIVE_NOUL with 0.0 always: it asserts no directive anywhere. This is the
    engine's current behaviour stated as a System One answer, so the typed path is proven
    inert before any model is attached. It is a baseline, not a detector."""

    id = "deterministic-baseline"
    provenance = "NO_JUDGEMENT_BASELINE"

    def ask(self, state: str, question) -> dict:
        return answer_receipt(question, 0.0, self.id, state, self.provenance)


def noul_to_integrity(answer: dict) -> float:
    """A directive probability of p means integrity 1-p. p=0 leaves integrity at 1.0, which
    is exactly today's behaviour; p=1 drives integrity to 0.0 and, under zero-pinning, forces
    REVIEW. A schema violation is never allowed to move the axis."""
    if answer.get("schema_violation") or answer.get("value") is None:
        return 1.0
    return max(0.0, min(1.0, 1.0 - float(answer["value"])))