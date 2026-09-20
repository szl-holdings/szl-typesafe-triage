# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Verbatim evidence verification.

The grounding guarantee: a model may only justify a label with text that
provably occurs in the input. Verification is a substring test -- no model, no
heuristic, no trust. An auditor re-checks every span with `in`.

Matching is case-insensitive and collapses runs of whitespace, because those
differences are artifacts of tokenization rather than fabrication. Anything
else -- paraphrase, summary, invention -- fails.
"""
from __future__ import annotations

from .axes import normalize

MIN_SPAN_CHARS = 3


def is_grounded(span: str, source: str) -> bool:
    """True when `span` occurs verbatim in `source` under normalization."""
    if len(span.strip()) < MIN_SPAN_CHARS:
        return False
    return normalize(span) in normalize(source)


def ungrounded_spans(spans: tuple[str, ...] | list[str], source: str) -> list[str]:
    """Every span that cannot be found in the source. Empty means grounded."""
    return [span for span in spans if not is_grounded(span, source)]
