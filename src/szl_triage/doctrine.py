# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Explicit doctrine dispositions: metadata that forbids action.

The engine's integrity axis detects text that *instructs the classifier*. It
does not detect text that *carries a governance disposition*, because the
estate's own vocabulary -- HOLD, productionAuthorized, UNKNOWN_NOT_INFERRED --
is absent from the triage lexicon.

Measured, 2026-09-20: every governance instruction of the day reached REVIEW
with ``integrity == 1.0`` and ``breadth == 0.0``. The engine refused because it
recognised none of the words, not because it understood it was being
instructed. A correct disposition reached without understanding is luck, and
luck does not survive rephrasing. See ``docs/doctrine-dispositions.md``.

This module closes that gap for the one case where the input states its own
authority. If a payload declares ``"disposition": "HOLD"`` or
``"productionAuthorized": false``, that declaration is terminal: no quantity of
lexical evidence may outvote it, and no model is consulted.

WHY THIS PARSES JSON INSTEAD OF MATCHING TEXT
---------------------------------------------
The first implementation matched strings and assumed ``"disposition": "hold"``
with a space after the colon. Real JSON writes ``"disposition":"HOLD"``. It
missed the actual handoff file it was written for. That is the third instance
today of the same defect class -- a plausible-looking matcher standing in for a
parser -- after substring keyword matching and the paraphrase bypass.

So: parse the structure when the input is structured, fall back to
whitespace-tolerant patterns when it is prose, and document what still escapes.
"""
from __future__ import annotations

import json
import re
from typing import Any

# Field name (underscore- and case-insensitive) -> values that forbid action.
DISPOSITION_FIELDS: dict[str, frozenset] = {
    "disposition": frozenset({"hold", "blocked", "rejected", "review"}),
    "productionauthorized": frozenset({False, "false"}),
    "productionauthorised": frozenset({False, "false"}),
    "automaticproductionpromotion": frozenset({False, "false"}),
}

# Bare tokens that are themselves refusals: they assert a fact is NOT known.
TOKEN_MARKERS: tuple[str, ...] = (
    "unknown_not_inferred",
    "not_inferred_from_reported_status",
    "pending_human_ratification",
)

# Whitespace- and quote-tolerant prose forms. Deliberately require a colon:
# that requirement is what keeps "the deployment is on hold" from matching.
FIELD_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r'"?disposition"?\s*:\s*"?(hold|blocked|rejected)"?', re.I), "disposition"),
    (re.compile(r'"?production_?authoris?zed"?\s*:\s*"?false"?', re.I), "productionAuthorized"),
    (re.compile(r'"?automatic_?production_?promotion"?\s*:\s*"?false"?', re.I), "automaticProductionPromotion"),
)


def _walk(node: Any, found: list[str]) -> None:
    """Collect forbidding fields anywhere in a parsed structure, at any depth."""
    if isinstance(node, dict):
        for key, value in node.items():
            normalized_key = str(key).strip().lower().replace("_", "")
            if normalized_key in DISPOSITION_FIELDS:
                comparable = value if isinstance(value, bool) else str(value).strip().lower()
                if comparable in DISPOSITION_FIELDS[normalized_key]:
                    found.append(f"{key}={value}")
            _walk(value, found)
    elif isinstance(node, list):
        for item in node:
            _walk(item, found)


def detect(text: str) -> tuple[str, ...]:
    """Return the dispositions in `text` that forbid action. Empty means clear."""
    found: list[str] = []
    stripped = text.strip()

    if stripped.startswith(("{", "[")):
        try:
            _walk(json.loads(stripped), found)
        except (ValueError, TypeError):
            pass  # Not valid JSON; the prose patterns below still apply.

    if not found:
        for pattern, name in FIELD_PATTERNS:
            if pattern.search(text):
                found.append(name)

    lowered = " ".join(text.split()).lower()
    for marker in TOKEN_MARKERS:
        if marker in lowered:
            found.append(marker)

    return tuple(dict.fromkeys(found))


def decide(text: str, policy, model=None, chain=None):
    """``pipeline.decide`` with a doctrine pre-check. Fails closed.

    A wrapper rather than a core edit: a first-class ``Tier.DOCTRINE`` requires
    changing ``contracts.py`` and re-running the full suite against the
    installed package. This composes and is additive, so nothing that currently
    passes can regress. Refusals here report ``Tier.GUARD`` with a rationale
    naming the disposition; the dedicated tier is a follow-up.
    """
    from .contracts import Decision, State, Tier, new_decision_id, sha256_text
    from .pipeline import decide as pipeline_decide

    dispositions = detect(text)
    if dispositions:
        decision = Decision(
            decision_id=new_decision_id(text),
            label="REVIEW",
            state=State.REVIEW,
            tier=Tier.GUARD,
            evidence=(),
            rationale=(
                f"explicit doctrine disposition forbids action: {list(dispositions)}",
                "terminal: lexical evidence cannot outvote a declared disposition",
                "model not consulted",
            ),
            policy_name=policy.name,
            policy_version=policy.version,
            input_sha256=sha256_text(text),
        )
        if chain is not None:
            chain.append(decision.to_dict())
        return decision

    return pipeline_decide(text, policy, model=model, chain=chain)
