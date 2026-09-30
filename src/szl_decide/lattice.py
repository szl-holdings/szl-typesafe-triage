# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Seat values: the interval lattice with two orders (INVENTION §2.1).

    I = { [lo, hi] : 0 <= lo <= hi <= 1 }

* Information order: I ⊑ J iff J ⊆ I ("J knows more"). Bottom is [0, 1],
  which is ABSTAIN / unknown.
* Truth order: componentwise on (lo, hi).

The corners are GO = [1, 1], NO_GO = [0, 0] and ABSTAIN = [0, 1]. On corners,
{NO_GO < ABSTAIN < GO} with AND = min is Kleene strong conjunction.

ABSTAIN has no scalar encoding anywhere: a seat value is an `Interval`, never a
float. Encoding ABSTAIN as 0.5 would admit, since 0.5 ** 0.25 = 0.8409 >= 0.80.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Optional

__all__ = [
    "Tri", "Interval", "IntervalError", "BOTTOM", "GO_I", "NO_GO_I",
    "kleene_and", "refines", "info_le", "truth_le", "corner", "from_tri", "check_interval",
]

INTERVAL_INVALID = "INTERVAL_INVALID"


class Tri(IntEnum):
    """Verdict on the corners, in truth order. AND is min (Kleene strong)."""

    NO_GO = 0
    ABSTAIN = 1
    GO = 2


class IntervalError(ValueError):
    """An interval outside 0 <= lo <= hi <= 1 (NaN, ±Inf, bool and non-numbers fail too)."""

    def __init__(self, detail: str) -> None:
        self.code = INTERVAL_INVALID
        super().__init__(f"{INTERVAL_INVALID}: {detail}")


def _endpoint(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise IntervalError(f"{name} is {type(value).__name__}, not a real number")
    try:
        x = float(value)
    except OverflowError:
        raise IntervalError(f"{name} is outside the finite float range") from None
    if not math.isfinite(x):
        raise IntervalError(f"{name}={x!r} is not finite")
    return x + 0.0  # -0.0 becomes 0.0, so equal intervals have equal bytes


def check_interval(lo: Any, hi: Any) -> tuple[float, float]:
    """Validated (lo, hi) as floats, or IntervalError. Shared by every re-check."""
    a, b = _endpoint("lo", lo), _endpoint("hi", hi)
    if not 0.0 <= a <= b <= 1.0:
        raise IntervalError(f"[{a!r}, {b!r}] is not inside 0 <= lo <= hi <= 1")
    return a, b


@dataclass(frozen=True, slots=True)
class Interval:
    """A seat value [lo, hi]. The constructor is the only way in; invalid input raises."""

    lo: float
    hi: float

    def __post_init__(self) -> None:
        a, b = check_interval(self.lo, self.hi)
        object.__setattr__(self, "lo", a)
        object.__setattr__(self, "hi", b)

    def refines(self, older: "Interval") -> bool:
        """True iff self ⊆ older, i.e. self is at or above older in the information order."""
        return refines(self, older)


GO_I = Interval(1.0, 1.0)
NO_GO_I = Interval(0.0, 0.0)
BOTTOM = Interval(0.0, 1.0)

_CORNERS = {Tri.GO: GO_I, Tri.NO_GO: NO_GO_I, Tri.ABSTAIN: BOTTOM}


def _need_interval(value: Any) -> Interval:
    if not isinstance(value, Interval):
        raise TypeError(f"expected Interval, got {type(value).__name__}")
    return value


def refines(newer: Interval, older: Interval) -> bool:
    """newer ⊆ older: the newer reading knows at least as much as the older one."""
    n, o = _need_interval(newer), _need_interval(older)
    return o.lo <= n.lo and n.hi <= o.hi


def info_le(a: Interval, b: Interval) -> bool:
    """a ⊑ b in the information order (b ⊆ a)."""
    return refines(b, a)


def truth_le(a: Interval, b: Interval) -> bool:
    """a <= b in the truth order (componentwise)."""
    x, y = _need_interval(a), _need_interval(b)
    return x.lo <= y.lo and x.hi <= y.hi


def corner(value: Interval) -> Optional[Tri]:
    """The Tri for a corner interval, or None for any other interval."""
    i = _need_interval(value)
    for tri, iv in _CORNERS.items():
        if i == iv:
            return tri
    return None


def from_tri(value: Tri) -> Interval:
    """The corner interval of a Tri."""
    if not isinstance(value, Tri):
        raise TypeError(f"expected Tri, got {type(value).__name__}")
    return _CORNERS[value]


def kleene_and(*values: Tri) -> Tri:
    """Kleene strong conjunction: the minimum in truth order.

    An empty conjunction raises instead of returning GO: nothing was checked,
    so nothing passes.
    """
    if not values:
        raise ValueError("kleene_and of nothing: an empty conjunction is not a pass")
    for v in values:
        if not isinstance(v, Tri):
            raise TypeError(f"expected Tri, got {type(v).__name__}")
    return min(values)
