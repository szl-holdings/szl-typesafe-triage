# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Policy loading and validation.

A policy is data, not code: versioned JSON that can be diffed in a pull
request and read by someone who does not write Python. Loading fails closed
-- a malformed policy raises rather than silently degrading to permissive
defaults.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_KEYS = frozenset(
    {"name", "version", "labels", "rules", "min_confidence", "min_margin"}
)

NORMALIZATIONS = frozenset({"sum", "top1", "top2"})

REVIEW_LABEL = "REVIEW"


class PolicyError(ValueError):
    """Raised when a policy cannot be trusted. Never suppressed."""


@dataclass(frozen=True)
class Policy:
    name: str
    version: str
    labels: tuple[str, ...]
    rules: dict[str, tuple[tuple[str, float], ...]]
    injection_phrases: tuple[str, ...]
    min_confidence: float
    min_margin: float
    normalization: str

    @property
    def classifiable(self) -> tuple[str, ...]:
        """Labels a decision may assert, excluding the REVIEW sink."""
        return tuple(label for label in self.labels if label != REVIEW_LABEL)

    def denominator(self, label: str) -> float:
        """Evidence baseline for a label.

        "sum"  -- every keyword must fire. Measured unreachable for real
                  inputs (see docs/calibration.md); retained so historical
                  scores stay reproducible.
        "top1" -- the strongest keyword defines sufficient evidence.
        "top2" -- two signals required. Measured too strict.
        """
        weights = sorted((weight for _, weight in self.rules[label]), reverse=True)
        if not weights:
            return 1.0
        if self.normalization == "top1":
            total = weights[0]
        elif self.normalization == "top2":
            total = sum(weights[:2])
        else:
            total = sum(weights)
        return total if total > 0 else 1.0


def _validate(raw: dict[str, Any]) -> None:
    missing = REQUIRED_KEYS - set(raw)
    if missing:
        raise PolicyError(f"policy missing required keys: {sorted(missing)}")
    normalization = raw.get("normalization", "sum")
    if normalization not in NORMALIZATIONS:
        raise PolicyError(f"unknown normalization: {normalization!r}")
    if REVIEW_LABEL not in raw["labels"]:
        raise PolicyError("policy must declare the REVIEW sink label")
    for label, terms in raw["rules"].items():
        if label not in raw["labels"]:
            raise PolicyError(f"rule for undeclared label: {label!r}")
        if not terms:
            raise PolicyError(f"label {label!r} has no terms")
        for term in terms:
            if not str(term.get("term", "")).strip():
                raise PolicyError(f"empty term in label {label!r}")
            weight = float(term.get("weight", 0.0))
            if not 0.0 < weight <= 1.0:
                raise PolicyError(f"weight out of range in {label!r}: {weight}")
    for bound in ("min_confidence", "min_margin"):
        value = float(raw[bound])
        if not 0.0 <= value <= 1.0:
            raise PolicyError(f"{bound} out of range: {value}")


def load(path: str | Path) -> Policy:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    _validate(raw)
    return Policy(
        name=raw["name"],
        version=raw["version"],
        labels=tuple(raw["labels"]),
        rules={
            label: tuple((t["term"], float(t["weight"])) for t in terms)
            for label, terms in raw["rules"].items()
        },
        injection_phrases=tuple(raw.get("injection_phrases", ())),
        min_confidence=float(raw["min_confidence"]),
        min_margin=float(raw["min_margin"]),
        normalization=raw.get("normalization", "sum"),
    )
