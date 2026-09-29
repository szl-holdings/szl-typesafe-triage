# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""The seat-value lattice (INVENTION §2.1): intervals with two orders, Kleene on corners.

A seat value is an `Interval`, never a bare float, and ABSTAIN is the interval
[0, 1], never a number such as 0.5.
"""
from __future__ import annotations

import itertools
import math

import pytest

from szl_decide import lattice
from szl_decide.lattice import (BOTTOM, GO_I, NO_GO_I, Interval, IntervalError, Tri, corner,
                                from_tri, info_le, kleene_and, refines, truth_le)

from . import _gen


# ------------------------------------------------------------------ Interval --

def test_corners_are_the_three_named_intervals():
    assert (GO_I.lo, GO_I.hi) == (1.0, 1.0)
    assert (NO_GO_I.lo, NO_GO_I.hi) == (0.0, 0.0)
    assert (BOTTOM.lo, BOTTOM.hi) == (0.0, 1.0)
    assert corner(GO_I) is Tri.GO
    assert corner(NO_GO_I) is Tri.NO_GO
    assert corner(BOTTOM) is Tri.ABSTAIN
    for t in Tri:
        assert corner(from_tri(t)) is t


def test_abstain_has_no_scalar_encoding():
    # 0.5 is not ABSTAIN: it is a point interval, not a corner. Encoding ABSTAIN
    # as 0.5 would admit, since 0.5 ** 0.25 = 0.8409 >= 0.80 (INVENTION §2.1).
    assert corner(Interval(0.5, 0.5)) is None
    assert Interval(0.5, 0.5) != BOTTOM
    assert 0.5 ** 0.25 >= 0.80
    assert [t.value for t in Tri] == [0, 1, 2]


@pytest.mark.parametrize("lo, hi", [
    (math.nan, 1.0), (0.0, math.nan), (math.nan, math.nan),
    (math.inf, 1.0), (0.0, math.inf), (-math.inf, 1.0),
    (-0.1, 1.0), (0.0, 1.1), (0.7, 0.6),
    (True, 1.0), (0.0, True), (None, 1.0), (0.0, None), ("0", 1.0), (0.0, "1"),
])
def test_invalid_interval_is_refused_at_construction(lo, hi):
    with pytest.raises(IntervalError):
        Interval(lo, hi)


def test_interval_error_is_a_value_error_with_a_code():
    with pytest.raises(ValueError) as info:
        Interval(math.nan, 1.0)
    assert info.value.code == "INTERVAL_INVALID"


def test_interval_normalises_ints_and_negative_zero():
    i = Interval(0, 1)
    assert type(i.lo) is float and type(i.hi) is float
    assert i == BOTTOM
    z = Interval(-0.0, -0.0)
    assert math.copysign(1.0, z.lo) == 1.0 and math.copysign(1.0, z.hi) == 1.0
    assert z == NO_GO_I


def test_interval_is_immutable():
    with pytest.raises(AttributeError):
        GO_I.lo = 0.0  # type: ignore[misc]


def test_corner_rejects_non_intervals():
    with pytest.raises(TypeError):
        corner(0.5)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        from_tri(2)  # type: ignore[arg-type]


# ------------------------------------------------------------------- orders --

def _sample(n: int, salt: int) -> list[Interval]:
    r = _gen.rng(salt)
    return [_gen.interval(r) for _ in range(n)]


def test_information_order_is_a_partial_order_with_bottom_least():
    xs = _sample(120, 1)
    for a in xs:
        assert info_le(a, a)
        assert info_le(BOTTOM, a)
        for b in xs:
            if info_le(a, b) and info_le(b, a):
                assert a == b
            for c in xs[:30]:
                if info_le(a, b) and info_le(b, c):
                    assert info_le(a, c)


def test_refines_means_the_newer_interval_is_inside_the_older():
    assert refines(Interval(0.2, 0.4), Interval(0.1, 0.5))
    assert not refines(Interval(0.1, 0.5), Interval(0.2, 0.4))
    assert refines(GO_I, BOTTOM) and refines(NO_GO_I, BOTTOM)
    assert not refines(GO_I, NO_GO_I)
    r = _gen.rng(2)
    for i in range(_gen.CASES):
        old = _gen.interval(r)
        new = _gen.refine(r, old)
        assert refines(new, old), i
        assert new.refines(old), i
        assert info_le(old, new), i


def test_truth_order_is_componentwise_and_has_the_corners_in_kleene_order():
    assert truth_le(NO_GO_I, BOTTOM) and truth_le(BOTTOM, GO_I) and truth_le(NO_GO_I, GO_I)
    assert not truth_le(GO_I, BOTTOM)
    xs = _sample(120, 3)
    for a in xs:
        assert truth_le(a, a)
        assert truth_le(NO_GO_I, a) and truth_le(a, GO_I)
        for b in xs:
            if truth_le(a, b) and truth_le(b, a):
                assert a == b


# ---------------------------------------------------------- Kleene on L3 --

def test_kleene_and_is_min_on_every_pair():
    for a, b in itertools.product(Tri, Tri):
        assert kleene_and(a, b) is min(a, b)
    assert kleene_and(Tri.GO, Tri.ABSTAIN) is Tri.ABSTAIN
    assert kleene_and(Tri.ABSTAIN, Tri.NO_GO) is Tri.NO_GO


def test_kleene_and_over_every_tuple_up_to_six():
    for k in range(1, 7):
        for combo in itertools.product(Tri, repeat=k):
            assert kleene_and(*combo) is min(combo)


def test_empty_conjunction_is_refused_not_a_pass():
    with pytest.raises(ValueError):
        kleene_and()


def test_kleene_and_rejects_non_tri_values():
    for bad in (2, 1.0, True, None, "GO"):
        with pytest.raises(TypeError):
            kleene_and(Tri.GO, bad)  # type: ignore[arg-type]


def test_module_exports_the_documented_names():
    for name in ("Tri", "Interval", "IntervalError", "BOTTOM", "GO_I", "NO_GO_I",
                 "kleene_and", "refines", "info_le", "truth_le", "corner", "from_tri"):
        assert name in lattice.__all__
