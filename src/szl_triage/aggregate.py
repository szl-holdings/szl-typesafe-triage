# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""The Lambda aggregator.

Weighted geometric mean over axis scores in [0,1]. Mirrors the contract of
`szl-holdings/szl-lambda-gate`: **any single zeroed axis drives the whole
aggregate to zero**. That non-compensatory property is the load-bearing
element of this package, not an implementation detail -- it is what makes a
zeroed integrity axis an unarguable refusal rather than a low score.

PROOF STATUS (corrected 2026-09-20, verbatim from the SZL formula corpus):

    Conjecture 1: Lambda is the UNIQUE aggregator satisfying A1-A5.
    Unconditional uniqueness is machine-checked FALSE (maxAgg counterexample);
    conditional Theorem U is proven.

An earlier revision of this file said "uniqueness remains Conjecture 1 (OPEN)".
That was softer than the doctrine it cited: "open" implies undecided, whereas
unconditional uniqueness is *disproven* by a named counterexample and what
holds is a conditional theorem. A1-A4 (Monotonicity, IsHomogeneous, Egyptian
inspectability, IsBounded) are PROVEN in Lean; see `szl-holdings/lutar-lean`,
DOI 10.5281/zenodo.20434308.

The roll-up is ADVISORY. It is not proven trust.

NOTE: `szl_receipt.lambda_gate.lambda_score` implements the same contract. This
is a third implementation of Lambda in the estate and should be replaced by an
import once a differential test confirms the two agree. If they disagree, one
of them is wrong and that matters more than the deduplication.
"""
from __future__ import annotations

import math
from typing import Mapping

EPSILON = 1e-12


def lambda_aggregate(axes: Mapping[str, float], weights: Mapping[str, float]) -> float:
    """Weighted geometric mean of `axes`. Returns 0.0 if any axis is 0.

    Raises KeyError if an axis has no declared weight: a silent default would
    let an unweighted axis quietly stop mattering.
    """
    if not axes:
        return 0.0
    total_weight = 0.0
    for name in axes:
        total_weight += float(weights[name])
    if total_weight <= 0.0:
        return 0.0

    accumulator = 0.0
    for name, value in axes.items():
        clamped = min(max(float(value), 0.0), 1.0)
        if clamped <= EPSILON:
            return 0.0
        accumulator += (float(weights[name]) / total_weight) * math.log(clamped)
    return round(math.exp(accumulator), 4)
