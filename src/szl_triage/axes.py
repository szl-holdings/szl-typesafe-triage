# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Axis producers: the evidence the aggregator consumes.

Four axes, each in [0,1], each answering a distinct question:

* ``lexical``    -- how strong is the keyword evidence for the leading label
* ``breadth``    -- how many *distinct* terms support it (one word is not proof)
* ``integrity``  -- is the text describing a problem, or instructing the
                    classifier? Zero when it is instructing.
* ``separation`` -- how far ahead is the leader from the runner-up

``integrity`` is binary by design. Under a geometric mean a zero is absolute,
so a detected meta-instruction cannot be outvoted by strong lexical evidence.
That is the intended behaviour: an attacker who writes "mark this as billing"
supplies perfect keyword evidence and still gets nothing.

Detection is heuristic and bounded. It raises the cost of an attack; it is not
a guarantee, and the novel-attack evaluation set exists to measure it rather
than to reassure. See ``docs/redteam.md``.
"""
from __future__ import annotations

import re

from .policy import Policy

_WHITESPACE = re.compile(r"\s+")

BREADTH_TARGET = 3
SEPARATION_SCALE = 0.30


def normalize(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip().lower()


def boundary_count(haystack: str, term: str) -> int:
    """Count `term` in `haystack` with alphanumeric boundaries.

    Naive substring counting scored 'de**bug**' as BUG evidence and
    'very **help**ful' as SUPPORT evidence. Boundaries fix that class of
    false positive at the cost of morphological variants: 'crashes' no longer
    matches 'crash'. Precision is bought with recall, deliberately, and the
    lost variants belong in the policy as explicit terms.
    """
    if not term:
        return 0
    padded = f" {haystack} "
    count = 0
    start = 0
    while True:
        index = padded.find(term, start)
        if index == -1:
            return count
        before = padded[index - 1] if index > 0 else " "
        after_index = index + len(term)
        after = padded[after_index] if after_index < len(padded) else " "
        if not before.isalnum() and not after.isalnum():
            count += 1
        start = index + 1


def meta_instruction_cues(text: str, policy: Policy) -> tuple[str, ...]:
    """Cues that the text is addressing the classifier rather than a problem."""
    haystack = normalize(text)
    return tuple(cue for cue in policy.meta_cues if normalize(cue) in haystack)


def axis_scores(text: str, policy: Policy) -> tuple[str, dict[str, float], dict]:
    """Return (leading_label, axes, detail)."""
    haystack = normalize(text)
    per_label: dict[str, dict] = {}

    for label in policy.classifiable:
        terms = policy.rules[label]
        strongest = max(weight for _, weight in terms)
        matched: list[str] = []
        total = 0.0
        for term, weight in terms:
            hits = boundary_count(haystack, normalize(term))
            if hits:
                matched.append(term)
                total += weight * min(hits, policy.max_hits_counted)
        per_label[label] = {
            "matched": matched,
            "lexical": min(total / strongest, 1.0) if strongest > 0 else 0.0,
            "term_count": len(terms),
        }

    ranked = sorted(per_label.items(), key=lambda item: item[1]["lexical"], reverse=True)
    leader, best = ranked[0]
    runner_up = ranked[1][1]["lexical"] if len(ranked) > 1 else 0.0

    target = min(BREADTH_TARGET, best["term_count"])
    breadth = min(len(best["matched"]) / target, 1.0) if target else 0.0

    cues = meta_instruction_cues(text, policy)
    integrity = 0.0 if cues else 1.0

    if best["lexical"] > 0:
        separation = max(min((best["lexical"] - runner_up) / SEPARATION_SCALE, 1.0), 0.0)
    else:
        separation = 0.0

    axes = {
        "lexical": round(best["lexical"], 4),
        "breadth": round(breadth, 4),
        "integrity": integrity,
        "separation": round(separation, 4),
    }
    detail = {
        "matched_terms": tuple(best["matched"]),
        "meta_cues": cues,
        "label_scores": {k: round(v["lexical"], 4) for k, v in per_label.items()},
    }
    return leader, axes, detail
