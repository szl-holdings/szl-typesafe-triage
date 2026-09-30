# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""szl_decide: the TINKUY decision engine (core).

This package holds the pure core: the interval lattice (`lattice`), the
szl.lambda/v1 roll-up (`lam`), the floors-and-Λ gate (`gate`), fan-in
completeness (`fanin`) and canonical bytes (`canon`). It is stdlib only and
never imports `szl_triage`; `szl_triage` may import it.

A seat value is an interval, never a bare float. Missing, NaN, ±Inf or invalid
input is bottom [0, 1] and never passes. An advisory second reader has no input
into the gate.

Nothing here is a signature over a decision: receipts are UNSIGNED_HONEST until
the owner pins a key. Nothing here uses Conjecture 1 (whether Λ is the only
aggregator with its axioms): CONJECTURE_1_NOT_USED.
"""
from __future__ import annotations

__version__ = "0.1.0"

#: Where the szl.decide predicate types resolve (INVENTION §8.1).
SPEC_URL_PREFIX = "https://a11oy.net/spec/"

SCHEMA_LAMBDA = "szl.lambda/v1"
SCHEMA_DECISION = "szl.decide.decision/v1"
SCHEMA_PLAN = "szl.decide.plan/v1"
SCHEMA_OVERLAY = "szl.decide.overlay/v1"
SCHEMA_LEDGER_ROW = "szl.decide.ledger-row/v1"
SCHEMA_TRACE = "szl.trace/v1"
SCHEMA_IDS = (SCHEMA_LAMBDA, SCHEMA_DECISION, SCHEMA_PLAN, SCHEMA_OVERLAY, SCHEMA_LEDGER_ROW,
              SCHEMA_TRACE)

#: Honesty labels carried into every receipt's `honesty` block.
UNSIGNED_HONEST = "UNSIGNED_HONEST"
CONJECTURE_1_NOT_USED = "CONJECTURE_1_NOT_USED"

__all__ = ["__version__", "SPEC_URL_PREFIX", "SCHEMA_IDS", "SCHEMA_LAMBDA", "SCHEMA_DECISION",
           "SCHEMA_PLAN", "SCHEMA_OVERLAY", "SCHEMA_LEDGER_ROW", "SCHEMA_TRACE",
           "UNSIGNED_HONEST", "CONJECTURE_1_NOT_USED"]
