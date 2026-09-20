# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Verbatim evidence verification.

The pipeline's grounding guarantee: a model may only justify a label with
text that provably occurs in the input. Verification is a substring test --
no model, no heuristic, no trust. An auditor can re-check every span with
`in`.

Matching is case-insensitive and collapses runs of whitespace, because those
differences are artifacts of tokenization rather than fabrication. Anything
else -- paraphrase, summary, invention -- fails.
"""
from __future__ import annotations

import re

_WHITESPACE = re.compile(r"\s+")

MIN_SPAN_CHARS = 3


def normalize(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip().lower()


def is_grounded(span: str, source: str) -> bool:
    """True when `span` occurs verbatim in `source` under normalization."""
    if len(span.strip()) < MIN_SPAN_CHARS:
        return False
    return normalize(span) in normalize(source)


def ungrounded_spans(spans: tuple[str, ...] | list[str], source: str) -> list[str]:
    """Every span that cannot be found in the source. Empty means grounded."""
    return [span for span in spans if not is_grounded(span, source)]
