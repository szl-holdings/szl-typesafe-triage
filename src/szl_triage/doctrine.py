# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Tier 2: explicit doctrine dispositions -- metadata that forbids action.

The integrity axis detects text that *instructs the classifier*. It does not
detect text that *carries a governance disposition*, because the estate's own
vocabulary is absent from the triage lexicon.

Measured 2026-09-20: every governance instruction of that day reached REVIEW
with ``integrity == 1.0`` and ``breadth == 0.0``. The engine refused because it
recognised none of the words, not because it understood it was being
instructed. A correct disposition reached without understanding is luck, and
luck does not survive rephrasing. See ``docs/doctrine-dispositions.md``.

If a payload declares ``"disposition": "HOLD"`` or
``"productionAuthorized": false``, that declaration is terminal.

DISPOSITIONS ARE POLICY DATA, NOT CODE
--------------------------------------
The first version of this module hardcoded the vocabulary in Python. Governance
vocabulary belongs in the policy file, where it can be diffed in a pull request
by someone who does not write Python. See ``doctrine_dispositions`` in the
policy schema.

WHY THIS PARSES JSON INSTEAD OF MATCHING TEXT
---------------------------------------------
The first implementation matched strings and assumed ``"disposition": "hold"``
with a space after the colon. Real JSON writes ``"disposition":"HOLD"``. It
missed the actual handoff file it was written for. That was the third instance
in one day of the same defect class -- a plausible-looking matcher standing in
for a parser -- after substring keyword matching and the paraphrase cue list.

So: parse the structure when the input is structured, fall back to
whitespace-tolerant patterns when it is prose, and document what escapes.
"""
from __future__ import annotations

import json
import re
from typing import Any

from .policy import Policy

# Prose fallbacks. The required colon is what keeps "the deployment is on hold"
# from matching; that single constraint is why the false-positive count is 0.
_FIELD_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r'"?disposition"?\s*:\s*"?(hold|blocked|rejected)"?', re.I), "disposition"),
    (re.compile(r'"?production_?authoris?zed"?\s*:\s*"?false"?', re.I), "productionAuthorized"),
    (re.compile(r'"?automatic_?production_?promotion"?\s*:\s*"?false"?', re.I), "automaticProductionPromotion"),
)


def _walk(node: Any, fields: dict[str, frozenset], found: list[str]) -> None:
    """Collect forbidding fields anywhere in a parsed structure, at any depth."""
    if isinstance(node, dict):
        for key, value in node.items():
            normalized = str(key).strip().lower().replace("_", "")
            if normalized in fields:
                comparable = value if isinstance(value, bool) else str(value).strip().lower()
                if comparable in fields[normalized]:
                    found.append(f"{key}={value}")
            _walk(value, fields, found)
    elif isinstance(node, list):
        for item in node:
            _walk(item, fields, found)


def detect(text: str, policy: Policy) -> tuple[str, ...]:
    """Return the dispositions in `text` that forbid action. Empty means clear."""
    fields = policy.disposition_fields or {}
    tokens = policy.disposition_tokens or ()
    found: list[str] = []
    stripped = text.strip()

    if fields and stripped.startswith(("{", "[")):
        try:
            _walk(json.loads(stripped), fields, found)
        except (ValueError, TypeError):
            pass  # Not valid JSON; the prose patterns below still apply.

    if fields and not found:
        for pattern, name in _FIELD_PATTERNS:
            if pattern.search(text):
                found.append(name)

    lowered = " ".join(text.split()).lower()
    for token in tokens:
        if token.lower() in lowered:
            found.append(token)

    return tuple(dict.fromkeys(found))
