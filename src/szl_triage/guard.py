# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Tier 1: adversarial guard.

Runs before any classifier and before any model. A matched phrase routes
straight to REVIEW and the model is never consulted, so no prompt can argue
the system out of a refusal.

This tier catches only the phrases enumerated in policy. It is deliberately
shallow, and the measured evidence says so: of 40 structurally novel attacks,
this guard caught 1. The integrity axis in `axes.py` carries the real load.
See `docs/redteam.md` for the numbers.
"""
from __future__ import annotations

from .axes import normalize
from .policy import Policy


def detect(text: str, policy: Policy) -> tuple[str, ...]:
    """Return the injection phrases present in `text`."""
    haystack = normalize(text)
    return tuple(p for p in policy.injection_phrases if normalize(p) in haystack)
