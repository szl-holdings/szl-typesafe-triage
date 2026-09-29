# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Fan-in completeness kappa (INVENTION §2.5).

The expected id set E is committed before any dispatch, as
E_digest = sha256(canonical_bytes(sorted(E))). At run time

    kappa(E, R) = 1  iff  the ids of the valid results R equal E as a multiset,
                          each exactly once;

otherwise kappa = 0 and `missing`, `extra` and `dup` say why. A count check is
not enough: r0, r1, r1, r3, r4 against r0..r4 has the right count.

As a seat value: complete is [1, 1]; an expected id that is still pending (and
nothing extra or duplicated) is bottom [0, 1]; anything else is [0, 0]. kappa
is a hard conjunct of the gate, never a graded Λ axis: one missing result of
200 at weight 0.25 would move Λ by a factor of only 0.998748.

`valid(R)` (schema, terminal status, id binding) is the caller's filter;
`fanin_kappa` receives the ids of the results that passed it.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable

from .canon import canonical_sha256
from .lattice import BOTTOM, GO_I, NO_GO_I, Interval

__all__ = ["Kappa", "FanInError", "fanin_kappa", "expected_digest", "check_kappa"]

FANIN_EXPECTED_INVALID = "FANIN_EXPECTED_INVALID"
FANIN_ID_INVALID = "FANIN_ID_INVALID"
FANIN_PENDING_INVALID = "FANIN_PENDING_INVALID"

_HEX = frozenset("0123456789abcdef")


class FanInError(ValueError):
    """Malformed fan-in input. Raised instead of returning any kappa, so it never passes."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


def _ids(name: str, values: Any, code: str) -> list[str]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Iterable):
        raise FanInError(code, f"{name} must be a collection of ids, got {type(values).__name__}")
    out = list(values)
    for v in out:
        if not isinstance(v, str) or not v:
            raise FanInError(code, f"{name} holds {v!r}; ids are non-empty strings")
    return out


def _expected(expected: Any) -> list[str]:
    e = _ids("expected", expected, FANIN_EXPECTED_INVALID)
    if not e:
        raise FanInError(FANIN_EXPECTED_INVALID, "the expected set is empty")
    if len(set(e)) != len(e):
        raise FanInError(FANIN_EXPECTED_INVALID, "the expected set holds a duplicate id")
    return e


def expected_digest(expected: Iterable[str]) -> str:
    """E_digest = sha256(canonical_bytes(sorted(E))), written before any dispatch."""
    return canonical_sha256(sorted(_expected(expected)))


def _sorted_str_tuple(value: Any) -> bool:
    return (isinstance(value, tuple) and all(isinstance(v, str) and v for v in value)
            and list(value) == sorted(set(value)))


def check_kappa(k: Any) -> None:
    """Raise TypeError / ValueError unless k is a self-consistent Kappa."""
    if not isinstance(k, Kappa):
        raise TypeError(f"expected Kappa, got {type(k).__name__}")
    if not isinstance(k.ok, bool):
        raise ValueError("ok must be a bool")
    for name in ("missing", "extra", "dup", "pending"):
        if not _sorted_str_tuple(getattr(k, name)):
            raise ValueError(f"{name} must be a sorted tuple of distinct non-empty ids")
    if not (isinstance(k.E_digest, str) and len(k.E_digest) == 64 and set(k.E_digest) <= _HEX):
        raise ValueError("E_digest must be 64 lowercase hex digits")
    faults = bool(k.missing or k.extra or k.dup or k.pending)
    if k.ok == faults:
        raise ValueError("ok must be True exactly when nothing is missing, extra, duplicated "
                         "or pending")
    if not set(k.pending) <= set(k.missing):
        raise ValueError("a pending id must also be missing")


@dataclass(frozen=True, slots=True)
class Kappa:
    ok: bool
    missing: tuple[str, ...]
    extra: tuple[str, ...]
    dup: tuple[str, ...]
    E_digest: str
    pending: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        check_kappa(self)

    @property
    def interval(self) -> Interval:
        """[1, 1] when complete; bottom while only pending ids are missing; else [0, 0]."""
        if self.ok:
            return GO_I
        if not self.extra and not self.dup and set(self.missing) == set(self.pending):
            return BOTTOM
        return NO_GO_I


def fanin_kappa(expected: Iterable[str], received: Iterable[str],
                pending: Iterable[str] = ()) -> Kappa:
    """kappa(E, R) with missing / extra / dup. `pending` names expected ids not yet terminal."""
    e = _expected(expected)
    r = _ids("received", received, FANIN_ID_INVALID)
    p = _ids("pending", pending, FANIN_PENDING_INVALID)
    e_set, counts = set(e), Counter(r)
    if not set(p) <= e_set:
        raise FanInError(FANIN_PENDING_INVALID, "a pending id is not in the expected set")
    if set(p) & set(counts):
        raise FanInError(FANIN_PENDING_INVALID, "an id is both pending and received")
    missing = tuple(sorted(e_set - set(counts)))
    extra = tuple(sorted(set(counts) - e_set))
    dup = tuple(sorted(x for x, c in counts.items() if c > 1))
    pend = tuple(sorted(set(p)))
    ok = not (missing or extra or dup or pend)
    return Kappa(ok=ok, missing=missing, extra=extra, dup=dup,
                 E_digest=canonical_sha256(sorted(e)), pending=pend)
