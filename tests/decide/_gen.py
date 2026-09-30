# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Seeded stdlib generator for the szl_decide property tests.

hypothesis is not a dev dependency, so every randomised test draws from
`random.Random(seed)` with a fixed seed. A failure therefore reproduces
exactly, and the case index is in the assertion message.
"""
from __future__ import annotations

import math
import random

from szl_decide.lattice import BOTTOM, GO_I, NO_GO_I, Interval

SEED = 20260929
CASES = 10_000

#: tau values every "for every tau" test covers, beside random draws:
#: the smallest subnormal, tiny, the band edges near 1, and 1 itself.
TAU_GRID = (5e-324, 1e-300, 1e-9, 0.1, 0.5, 0.65, 0.8, 0.999999999, 1.0)


def rng(salt: int = 0) -> random.Random:
    return random.Random(SEED + salt)


def weights(r: random.Random, k: int) -> list[float]:
    """k positive weights whose fsum is within 1e-12 of 1 (the v1 contract)."""
    raw = [r.uniform(0.05, 1.0) for _ in range(k)]
    total = math.fsum(raw)
    out = [x / total for x in raw]
    assert abs(math.fsum(out) - 1.0) <= 1e-12
    return out


def floors(r: random.Random, k: int) -> list[float]:
    """Floors in (0, 1]; about one in ten is exactly 1.0."""
    return [1.0 if r.random() < 0.1 else r.uniform(0.01, 0.99) for _ in range(k)]


def tau(r: random.Random) -> float:
    """tau in (0, 1]."""
    roll = r.random()
    if roll < 0.05:
        return 1.0
    if roll < 0.10:
        return r.choice(TAU_GRID)
    return r.uniform(1e-6, 1.0)


def interval(r: random.Random) -> Interval:
    """15% each of the GO, NO_GO and bottom corners; otherwise a random interval."""
    roll = r.random()
    if roll < 0.15:
        return GO_I
    if roll < 0.30:
        return NO_GO_I
    if roll < 0.45:
        return BOTTOM
    a, b = r.random(), r.random()
    return Interval(min(a, b), max(a, b))


def refine(r: random.Random, older: Interval) -> Interval:
    """A random interval J with J inside `older` (J refines older)."""
    a = r.uniform(older.lo, older.hi)
    b = r.uniform(older.lo, older.hi)
    lo, hi = min(a, b), max(a, b)
    if r.random() < 0.2:
        lo = hi  # a point refinement
    lo = min(max(lo, older.lo), older.hi)
    hi = max(min(hi, older.hi), lo)
    return Interval(lo, hi)


def raise_endpoints(r: random.Random, base: Interval) -> Interval:
    """An interval that is >= base in the truth order (both endpoints raised or kept)."""
    lo = r.uniform(base.lo, 1.0)
    hi = r.uniform(max(base.hi, lo), 1.0)
    return Interval(lo, hi)


def point_in(r: random.Random, box: Interval) -> float:
    return r.uniform(box.lo, box.hi)
