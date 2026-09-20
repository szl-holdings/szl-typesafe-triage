# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Policy loading and validation.

A policy is data, not code: versioned JSON that can be diffed in a pull
request and read by someone who does not write Python. Loading fails closed --
a malformed policy raises rather than degrading to a permissive default.

Policy v3 replaces the bespoke `normalization` modes of v1/v2 with the Lambda
aggregator (see `docs/calibration.md` and `docs/redteam.md`). Both earlier
modes were measurably broken: `sum` was mathematically unreachable, and
`top1` let a single keyword reach confidence 1.0. Neither is retained as a
live option, because keeping a known-broken scorer selectable is not
backwards compatibility, it is a trap.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_KEYS = frozenset({
    "name", "version", "labels", "rules",
    "axis_weights", "lambda_threshold", "meta_cues",
})

REQUIRED_AXES = frozenset({"lexical", "breadth", "integrity", "separation"})

REVIEW_LABEL = "REVIEW"

DEFAULT_MAX_HITS = 2


class PolicyError(ValueError):
    """Raised when a policy cannot be trusted. Never suppressed."""


@dataclass(frozen=True)
class Policy:
    name: str
    version: str
    labels: tuple[str, ...]
    rules: dict[str, tuple[tuple[str, float], ...]]
    injection_phrases: tuple[str, ...]
    meta_cues: tuple[str, ...]
    axis_weights: dict[str, float]
    lambda_threshold: float
    max_hits_counted: int = DEFAULT_MAX_HITS

    @property
    def classifiable(self) -> tuple[str, ...]:
        """Labels a decision may assert, excluding the REVIEW sink."""
        return tuple(label for label in self.labels if label != REVIEW_LABEL)


def _validate(raw: dict[str, Any]) -> None:
    missing = REQUIRED_KEYS - set(raw)
    if missing:
        raise PolicyError(f"policy missing required keys: {sorted(missing)}")

    if REVIEW_LABEL not in raw["labels"]:
        raise PolicyError("policy must declare the REVIEW sink label")

    declared_axes = set(raw["axis_weights"])
    if declared_axes != REQUIRED_AXES:
        raise PolicyError(
            f"axis_weights must declare exactly {sorted(REQUIRED_AXES)}, got {sorted(declared_axes)}"
        )
    for axis, weight in raw["axis_weights"].items():
        if float(weight) <= 0.0:
            raise PolicyError(f"axis weight must be positive: {axis}={weight}")

    threshold = float(raw["lambda_threshold"])
    if not 0.0 < threshold <= 1.0:
        raise PolicyError(f"lambda_threshold out of range: {threshold}")

    if not raw["meta_cues"]:
        raise PolicyError("meta_cues must not be empty: the integrity axis would never fire")

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
        meta_cues=tuple(raw["meta_cues"]),
        axis_weights={k: float(v) for k, v in raw["axis_weights"].items()},
        lambda_threshold=float(raw["lambda_threshold"]),
        max_hits_counted=int(raw.get("max_hits_counted", DEFAULT_MAX_HITS)),
    )
