# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""The gate: per-seat hard floors AND interval-Λ (INVENTION §2.2-§2.3).

With lo~ and hi~ the floored endpoints (an endpoint below its seat's floor
becomes 0):

    D = GO      if Λ_w(lo~) is above tau (outside the tie band)
        NO_GO   if Λ_w(hi~) is below tau (outside the band), or some hi_k < f_k
        ABSTAIN otherwise, and whenever either endpoint is inside the band

Comparisons are in log space with `lam.TIE_EPS` (1e-9), the same band the
scalar `lam.gate_v1` uses.

Fail closed by type (I1): every seat in the policy is mandatory. A missing
reading, a reading that is not a valid `SeatReading` (NaN, ±Inf, bool,
inverted, forged), or a reading for another seat counts as bottom [0, 1], so
the verdict is at best ABSTAIN. A seat whose upper end is under its floor
vetoes for every tau (I2). A reading for a seat the policy does not name caps
the verdict below GO. An invalid policy gives ABSTAIN with its error code.
Fan-in kappas are hard conjuncts, never Λ axes.

The gate takes no second-reader input: nothing here can be reached by an
advisory reader.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal, Mapping, Optional

from . import lam
from .canon import is_f64_literal
from .fanin import Kappa, check_kappa
from .lattice import BOTTOM, Interval, IntervalError, Tri, check_interval, corner

__all__ = [
    "ReasonClass", "SeatReading", "Seat", "Policy", "PolicyError", "GateResult",
    "floored", "gate", "binding_stage", "failing_set", "COST_CLASSES",
]

COST_CLASSES = ("FREE_DETERMINISTIC", "PAID", "VOLATILE_FETCH")

# Gate result codes.
OK = "OK"
VETO = "VETO"
BELOW_TAU = "BELOW_TAU"
NUMERIC_TIE = "NUMERIC_TIE"
UNDETERMINED = "UNDETERMINED"
MISSING_READING = "MISSING_READING"
INVALID_READING = "INVALID_READING"
UNEXPECTED_READING = "UNEXPECTED_READING"
FANIN_INCOMPLETE = "FANIN_INCOMPLETE"
FANIN_PENDING = "FANIN_PENDING"
FANIN_INVALID = "FANIN_INVALID"

# Policy error codes (weights and tau use the szl.lambda/v1 codes).
SEAT_INVALID = "SEAT_INVALID"
POLICY_SEATS_INVALID = "POLICY_SEATS_INVALID"
POLICY_SEAT_DUPLICATE = "POLICY_SEAT_DUPLICATE"
POLICY_FIELD_INVALID = "POLICY_FIELD_INVALID"
POLICY_ALPHA_INVALID = "POLICY_ALPHA_INVALID"


class ReasonClass(str, Enum):
    NONE = "NONE"
    VETO = "VETO"
    EVIDENCE_INSUFFICIENT = "EVIDENCE_INSUFFICIENT"
    IN_BAND = "IN_BAND"
    POLICY_HOLD = "POLICY_HOLD"
    UNKNOWN = "UNKNOWN"
    SYSTEM = "SYSTEM"


class PolicyError(ValueError):
    """A seat or policy outside its contract. ``code`` names the rule."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


def _is_real(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _str_tuple(value: Any) -> bool:
    return isinstance(value, tuple) and all(isinstance(v, str) for v in value)


def _check_reading(r: Any) -> None:
    """Raise TypeError / ValueError unless r is a well-formed SeatReading."""
    if not isinstance(r, SeatReading):
        raise TypeError(f"expected SeatReading, got {type(r).__name__}")
    if not isinstance(r.seat, str) or not r.seat:
        raise ValueError("seat must be a non-empty string")
    if not isinstance(r.interval, Interval):
        raise TypeError(f"interval must be an Interval, got {type(r.interval).__name__}")
    check_interval(r.interval.lo, r.interval.hi)
    if not isinstance(r.reason_code, str) or not r.reason_code:
        raise ValueError("reason_code must be a non-empty string")
    if not isinstance(r.reason_class, ReasonClass):
        raise TypeError("reason_class must be a ReasonClass")
    if not _str_tuple(r.evidence_digests) or not _str_tuple(r.missing_slots):
        raise TypeError("evidence_digests and missing_slots must be tuples of strings")
    if r.score_f64 is not None and not is_f64_literal(r.score_f64):
        raise ValueError("score_f64 must be None or an 'f64:<hex>' literal")


@dataclass(frozen=True, slots=True)
class SeatReading:
    """One seat's value. `score_f64` is a receipt-only raw score; gate() never reads it."""

    seat: str
    interval: Interval
    reason_code: str
    reason_class: ReasonClass
    evidence_digests: tuple[str, ...] = ()
    missing_slots: tuple[str, ...] = ()
    score_f64: Optional[str] = None

    def __post_init__(self) -> None:
        _check_reading(self)


def _check_seat(s: Any) -> None:
    if not isinstance(s, Seat):
        raise PolicyError(SEAT_INVALID, f"expected Seat, got {type(s).__name__}")
    for name in ("id", "scope", "owner", "version"):
        value = getattr(s, name)
        if not isinstance(value, str) or not value:
            raise PolicyError(SEAT_INVALID, f"{name} must be a non-empty string")
    if not _is_real(s.floor) or not math.isfinite(s.floor) or not 0 < s.floor <= 1:
        raise PolicyError(SEAT_INVALID, f"seat {s.id!r}: floor {s.floor!r} is not in (0, 1]")
    if not _is_real(s.weight) or not math.isfinite(s.weight) or not s.weight > 0:
        raise PolicyError(SEAT_INVALID, f"seat {s.id!r}: weight {s.weight!r} is not > 0")
    if not isinstance(s.reads, frozenset) or not all(isinstance(x, str) for x in s.reads):
        raise PolicyError(SEAT_INVALID, f"seat {s.id!r}: reads must be a frozenset of strings")
    if s.cost_class not in COST_CLASSES:
        raise PolicyError(SEAT_INVALID, f"seat {s.id!r}: cost_class {s.cost_class!r}")
    if not isinstance(s.calibrated, bool):
        raise PolicyError(SEAT_INVALID, f"seat {s.id!r}: calibrated must be a bool")


@dataclass(frozen=True, slots=True)
class Seat:
    id: str
    scope: str
    floor: float
    weight: float
    owner: str
    version: str
    reads: frozenset[str]
    cost_class: Literal["FREE_DETERMINISTIC", "PAID", "VOLATILE_FETCH"]
    calibrated: bool = False

    def __post_init__(self) -> None:
        _check_seat(self)
        object.__setattr__(self, "floor", float(self.floor))
        object.__setattr__(self, "weight", float(self.weight))


def _check_policy(p: Any) -> None:
    if not isinstance(p, Policy):
        raise PolicyError(POLICY_FIELD_INVALID, f"expected Policy, got {type(p).__name__}")
    if not isinstance(p.seats, tuple) or not p.seats:
        raise PolicyError(POLICY_SEATS_INVALID, "seats must be a non-empty tuple")
    for s in p.seats:
        _check_seat(s)
    ids = [s.id for s in p.seats]
    if len(set(ids)) != len(ids):
        raise PolicyError(POLICY_SEAT_DUPLICATE, "seat ids must not repeat")
    try:
        lam.check_tau(p.tau)
        # Validates the weights as declared (no renormalisation) with the v1 codes.
        lam.log_lambda_w([1.0] * len(p.seats), [s.weight for s in p.seats])
    except lam.LambdaContractError as err:
        raise PolicyError(err.code, err.detail) from None
    for name in ("policy_rev", "lambda_impl_sha", "tau_source"):
        value = getattr(p, name)
        if not isinstance(value, str) or not value:
            raise PolicyError(POLICY_FIELD_INVALID, f"{name} must be a non-empty string")
    a = p.alpha_council_bound
    if a is not None:
        if not _is_real(a) or not math.isfinite(a) or a < 0:
            raise PolicyError(POLICY_ALPHA_INVALID, f"alpha_council_bound {a!r}")
        if not any(s.calibrated for s in p.seats):
            raise PolicyError(POLICY_ALPHA_INVALID,
                              "alpha_council_bound is set but no seat is calibrated")


@dataclass(frozen=True, slots=True)
class Policy:
    seats: tuple[Seat, ...]
    tau: float
    policy_rev: str
    lambda_impl_sha: str
    tau_source: str  # e.g. "szl-lambda-gate@<sha>:frontier/model_admit_contract.v1.json"
    alpha_council_bound: Optional[float] = None  # Σ α_k over calibrated seats (§2.8)

    def __post_init__(self) -> None:
        _check_policy(self)
        object.__setattr__(self, "tau", float(self.tau))
        if self.alpha_council_bound is not None:
            object.__setattr__(self, "alpha_council_bound", float(self.alpha_council_bound))


@dataclass(frozen=True, slots=True)
class GateResult:
    """Verdict, the code that explains it, and both Λ endpoints (None on a contract error)."""

    verdict: Tri
    code: str
    lambda_lo: Optional[float]
    lambda_hi: Optional[float]
    log_lo: Optional[float]
    log_hi: Optional[float]


def floored(interval: Interval, floor: float) -> Interval:
    """φ_f([lo, hi]) = [lo·1[lo >= f], hi·1[hi >= f]]; monotone in both orders."""
    if not isinstance(interval, Interval):
        raise TypeError(f"expected Interval, got {type(interval).__name__}")
    lo = interval.lo if interval.lo >= floor else 0.0
    hi = interval.hi if interval.hi >= floor else 0.0
    return Interval(lo, hi)


def _effective(readings: Any, seat: Seat) -> tuple[Interval, str, Optional[str]]:
    """(interval, reason_code, fault) for one mandatory seat. fault is None if the reading is valid."""
    value = readings.get(seat.id) if isinstance(readings, Mapping) else None
    if value is None:
        return BOTTOM, MISSING_READING, MISSING_READING
    try:
        _check_reading(value)
    except (TypeError, ValueError, IntervalError, AttributeError):
        return BOTTOM, INVALID_READING, INVALID_READING
    if value.seat != seat.id:
        return BOTTOM, INVALID_READING, INVALID_READING
    return value.interval, value.reason_code, None


def binding_stage(policy: Policy) -> Literal["floors", "lambda"]:
    """Lemma 2.6: "floors" iff Λ_w(f) is above tau outside the tie band.

    Then every reading that clears all floors is GO, so the Λ stage is inert.
    At Λ_w(f) within the band of tau an all-at-floor reading is a tie, so Λ binds.
    """
    _check_policy(policy)
    log_f = lam.log_lambda_w([s.floor for s in policy.seats], [s.weight for s in policy.seats])
    outcome = lam.compare_log(log_f, math.log(policy.tau))
    return "floors" if outcome == lam.ABOVE else "lambda"


def failing_set(readings: Mapping[str, SeatReading],
                policy: Policy) -> tuple[tuple[str, str, str], ...]:
    """(seat, "VETO" | "ABSTAIN", reason_code) in policy order.

    VETO: hi < floor. ABSTAIN: lo < floor <= hi. Missing or invalid readings
    count as bottom and so appear as ABSTAIN.
    """
    _check_policy(policy)
    out = []
    for seat in policy.seats:
        iv, code, _ = _effective(readings, seat)
        if iv.hi < seat.floor:
            out.append((seat.id, "VETO", code))
        elif iv.lo < seat.floor:
            out.append((seat.id, "ABSTAIN", code))
    return tuple(out)


def _fanin_verdict(value: Any) -> tuple[Tri, str]:
    try:
        check_kappa(value)
    except (TypeError, ValueError, AttributeError):
        return Tri.ABSTAIN, FANIN_INVALID
    tri = corner(value.interval)
    if tri is Tri.GO:
        return Tri.GO, OK
    if tri is Tri.ABSTAIN:
        return Tri.ABSTAIN, FANIN_PENDING
    return Tri.NO_GO, FANIN_INCOMPLETE


def _abstain(code: str) -> GateResult:
    return GateResult(Tri.ABSTAIN, code, None, None, None, None)


def gate(readings: Mapping[str, SeatReading], policy: Policy,
         fanins: Optional[Mapping[str, Kappa]] = None) -> GateResult:
    """D(I; f, w, tau) AND every fan-in kappa. Total: bad input gives ABSTAIN, never GO."""
    try:
        _check_policy(policy)
    except PolicyError as err:
        return _abstain(err.code)
    except (TypeError, ValueError, AttributeError):  # a forged object missing fields
        return _abstain(POLICY_FIELD_INVALID)
    seats = policy.seats
    weights = [s.weight for s in seats]

    faults = []
    lo, hi = [], []
    for seat in seats:
        iv, _, fault = _effective(readings, seat)
        if fault is not None:
            faults.append(fault)
        f = floored(iv, seat.floor)
        lo.append(f.lo)
        hi.append(f.hi)

    try:
        log_lo = lam.log_lambda_w(lo, weights)
        log_hi = lam.log_lambda_w(hi, weights)
    except lam.LambdaContractError as err:  # unreachable after _check_policy; fail closed
        return _abstain(err.code)
    log_tau = math.log(policy.tau)
    lambda_lo = 0.0 if log_lo == -math.inf else math.exp(log_lo)
    lambda_hi = 0.0 if log_hi == -math.inf else math.exp(log_hi)

    hi_cmp = lam.compare_log(log_hi, log_tau)
    lo_cmp = lam.compare_log(log_lo, log_tau)
    if log_hi == -math.inf:
        verdict, code = Tri.NO_GO, VETO
    elif hi_cmp == lam.BELOW:
        verdict, code = Tri.NO_GO, BELOW_TAU
    elif hi_cmp == lam.ABOVE and lo_cmp == lam.ABOVE and not faults:
        verdict, code = Tri.GO, OK
    elif INVALID_READING in faults:
        verdict, code = Tri.ABSTAIN, INVALID_READING
    elif MISSING_READING in faults:
        verdict, code = Tri.ABSTAIN, MISSING_READING
    elif hi_cmp == lam.TIE or lo_cmp == lam.TIE:
        verdict, code = Tri.ABSTAIN, NUMERIC_TIE
    else:
        verdict, code = Tri.ABSTAIN, UNDETERMINED

    if verdict is Tri.GO:
        known = {s.id for s in seats}
        if not isinstance(readings, Mapping) or any(k not in known for k in readings):
            verdict, code = Tri.ABSTAIN, UNEXPECTED_READING

    if fanins is not None:
        if not isinstance(fanins, Mapping):
            if verdict > Tri.ABSTAIN:
                verdict, code = Tri.ABSTAIN, FANIN_INVALID
        else:
            for key in sorted(fanins, key=str):
                v, c = _fanin_verdict(fanins[key])
                if v < verdict:
                    verdict, code = v, c

    return GateResult(verdict, code, lambda_lo, lambda_hi, log_lo, log_hi)
