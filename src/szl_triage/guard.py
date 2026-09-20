# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Tier 1: adversarial guard.

Runs before any classifier and before any model. A matched pattern routes
straight to REVIEW and the model is never consulted, so no prompt can argue
the system out of a refusal.

Detection is intentionally shallow and honest about it: literal phrase
matching over normalized text catches the patterns enumerated in policy and
nothing more. Robustness against unseen phrasings is an empirical question,
measured against a held-out novel-attack set rather than asserted here.
"""
from __future__ import annotations

from .evidence import normalize
from .policy import Policy


def detect(text: str, policy: Policy) -> tuple[str, ...]:
    """Return the injection phrases present in `text`."""
    haystack = normalize(text)
    return tuple(p for p in policy.injection_phrases if normalize(p) in haystack)
