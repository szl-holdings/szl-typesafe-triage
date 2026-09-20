# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Typed contracts for the triage pipeline.

Every value that crosses a tier boundary is defined here. Nothing in this
module imports a machine-learning framework: the contracts must be readable,
testable, and verifiable on a laptop with no GPU.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

SCHEMA = "szl.triage.decision/v3"


class State(str, Enum):
    """Terminal disposition of an input."""

    MEASURED = "MEASURED"
    REVIEW = "REVIEW"


class Tier(str, Enum):
    """Which tier produced the disposition.

    Recorded on every decision so an auditor can tell *who decided* without
    re-running anything. GUARD, DOCTRINE and VALIDATOR outcomes are always
    REVIEW.

    DOCTRINE was added in 0.4.0. It is a breaking change for any consumer that
    switches exhaustively on this enum, which is why the minor version moved.
    """

    GUARD = "GUARD"
    DOCTRINE = "DOCTRINE"
    ENGINE = "ENGINE"
    MODEL = "MODEL"
    VALIDATOR = "VALIDATOR"


def canonical(value: Any) -> str:
    """Deterministic JSON: sorted keys, no incidental whitespace."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ModelProposal:
    """What a model is permitted to return. Deliberately minimal.

    A proposal is untrusted. It carries no authority and no confidence
    number: a language model's self-reported probability is not evidence.
    Authority comes from `evidence` surviving verbatim verification.
    """

    label: str
    evidence: tuple[str, ...]
    rationale: str


@dataclass(frozen=True)
class Decision:
    """A triage disposition with its provenance.

    `axes` and `lambda_value` are recorded so a reader can see *why* the
    aggregate landed where it did. `dispositions` records governance metadata
    that forbade action, as structured data rather than only as prose inside
    `rationale` -- an auditor should be able to filter on it.
    """

    decision_id: str
    label: str
    state: State
    tier: Tier
    evidence: tuple[str, ...]
    rationale: tuple[str, ...]
    policy_name: str
    policy_version: str
    input_sha256: str
    scores: dict[str, float] = field(default_factory=dict)
    axes: dict[str, float] = field(default_factory=dict)
    lambda_value: float = 0.0
    dispositions: tuple[str, ...] = ()
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "decision_id": self.decision_id,
            "label": self.label,
            "state": self.state.value,
            "tier": self.tier.value,
            "evidence": list(self.evidence),
            "rationale": list(self.rationale),
            "policy_name": self.policy_name,
            "policy_version": self.policy_version,
            "input_sha256": self.input_sha256,
            "scores": self.scores,
            "axes": self.axes,
            "lambda": self.lambda_value,
            "dispositions": list(self.dispositions),
        }

    def to_json(self) -> str:
        return canonical(self.to_dict())


def new_decision_id(text: str) -> str:
    return f"szl.triage/{sha256_text(text)[:16]}"
