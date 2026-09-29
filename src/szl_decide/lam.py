# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""szl.lambda/v1 inside szl_decide: a stdlib port of the szl-lambda-gate reference.

    Λ_w(x) = ∏_k x_k^{w_k} = exp(fsum_k(w_k · log x_k)),   Λ = 0 if some x_k == 0

This is the same algorithm as `reference/szl_lambda_v1.py` in
szl-holdings/szl-lambda-gate (merged in PR #53), so it matches the vendored
vectors in `spec/lambda_v1_vectors.json` bit for bit, with the same error codes
and precedence. It does not import szl-lambda-gate, which needs torch.

Contract (every violation raises ``LambdaContractError(code)``; nothing is
clamped, renormalised, defaulted or rounded):

* ``axes`` and ``weights`` are lists or tuples of real numbers (``bool`` is not
  a number), of equal, non-zero length;
* every axis is finite and 0 <= x_k <= 1;
* every weight is finite and w_k > 0, and |fsum(w) - 1| <= 1e-12.

Checks run in phases, each over every element, so the reported code does not
depend on axis order::

    LAMBDA_TYPE_INVALID (container) > LAMBDA_EMPTY > LAMBDA_LENGTH_MISMATCH
    > LAMBDA_TYPE_INVALID (element) > LAMBDA_NONFINITE_AXIS
    > LAMBDA_AXIS_OUT_OF_RANGE > LAMBDA_NONFINITE_WEIGHT
    > LAMBDA_WEIGHT_NONPOSITIVE > LAMBDA_WEIGHT_SUM

Comparisons against tau are made in log space on the unrounded value, with one
tie band, TIE_EPS = 1e-9, shared by the scalar gate here and by `gate.gate`.
Λ is an advisory roll-up. Nothing here depends on Conjecture 1 (whether Λ is the
only aggregator with its axioms; its status in this repo is stated in
`szl_triage.aggregate`).
"""
from __future__ import annotations

import math
from typing import Any, Optional, Tuple

SCHEMA = "szl.lambda/v1"
WEIGHT_SUM_TOL = 1e-12
TIE_EPS = 1e-9

TYPE_INVALID = "LAMBDA_TYPE_INVALID"
EMPTY = "LAMBDA_EMPTY"
LENGTH_MISMATCH = "LAMBDA_LENGTH_MISMATCH"
NONFINITE_AXIS = "LAMBDA_NONFINITE_AXIS"
AXIS_OUT_OF_RANGE = "LAMBDA_AXIS_OUT_OF_RANGE"
NONFINITE_WEIGHT = "LAMBDA_NONFINITE_WEIGHT"
WEIGHT_NONPOSITIVE = "LAMBDA_WEIGHT_NONPOSITIVE"
WEIGHT_SUM = "LAMBDA_WEIGHT_SUM"
TAU_INVALID = "LAMBDA_TAU_INVALID"

#: Every error code, in precedence order (the gate checks tau before Λ).
ERROR_CODES = (
    TYPE_INVALID,
    EMPTY,
    LENGTH_MISMATCH,
    NONFINITE_AXIS,
    AXIS_OUT_OF_RANGE,
    NONFINITE_WEIGHT,
    WEIGHT_NONPOSITIVE,
    WEIGHT_SUM,
    TAU_INVALID,
)

GO = "GO"
NO_GO = "NO_GO"
ABSTAIN = "ABSTAIN"
BLOCK = "BLOCK"
VERDICTS = (GO, NO_GO, ABSTAIN, BLOCK)

ZERO_VETO = "ZERO_VETO"
BELOW_TAU = "BELOW_TAU"
NUMERIC_TIE = "NUMERIC_TIE"

#: Outcome of a log-space compare against tau.
ABOVE = "ABOVE"
BELOW = "BELOW"
TIE = "TIE"


class LambdaContractError(ValueError):
    """An input outside the szl.lambda/v1 contract. ``code`` is one of ERROR_CODES."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


def _is_real(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_nonfinite(value: Any) -> bool:
    # ints are always finite; only floats can be NaN or ±Inf.
    return isinstance(value, float) and not math.isfinite(value)


def _validate(axes: Any, weights: Any) -> None:
    for name, seq in (("axes", axes), ("weights", weights)):
        if not isinstance(seq, (list, tuple)):
            raise LambdaContractError(
                TYPE_INVALID, f"{name} must be a list or tuple, got {type(seq).__name__}")
    if len(axes) == 0 or len(weights) == 0:
        raise LambdaContractError(EMPTY, f"len(axes)={len(axes)}, len(weights)={len(weights)}")
    if len(axes) != len(weights):
        raise LambdaContractError(
            LENGTH_MISMATCH, f"len(axes)={len(axes)} != len(weights)={len(weights)}")
    for name, seq in (("axes", axes), ("weights", weights)):
        for i, value in enumerate(seq):
            if not _is_real(value):
                raise LambdaContractError(
                    TYPE_INVALID, f"{name}[{i}] is {type(value).__name__}, not a real number")
    for i, x in enumerate(axes):
        if _is_nonfinite(x):
            raise LambdaContractError(NONFINITE_AXIS, f"axes[{i}]={x!r}")
    for i, x in enumerate(axes):
        if not 0 <= x <= 1:
            raise LambdaContractError(AXIS_OUT_OF_RANGE, f"axes[{i}]={x!r} is outside [0, 1]")
    for i, w in enumerate(weights):
        if _is_nonfinite(w):
            raise LambdaContractError(NONFINITE_WEIGHT, f"weights[{i}]={w!r}")
    for i, w in enumerate(weights):
        if not w > 0:
            raise LambdaContractError(WEIGHT_NONPOSITIVE, f"weights[{i}]={w!r} is not > 0")
    try:
        total = math.fsum(weights)
    except OverflowError:
        raise LambdaContractError(WEIGHT_SUM, "sum of weights overflows a float") from None
    if not abs(total - 1.0) <= WEIGHT_SUM_TOL:
        raise LambdaContractError(
            WEIGHT_SUM, f"fsum(weights)={total!r} is not within {WEIGHT_SUM_TOL} of 1")


def log_lambda_w(axes: Any, weights: Any) -> float:
    """log Λ_w(x) = fsum(w_k · log x_k); -inf if some axis is 0. Raises LambdaContractError."""
    _validate(axes, weights)
    if any(x == 0 for x in axes):
        return -math.inf
    return math.fsum(float(w) * math.log(float(x)) for x, w in zip(axes, weights))


def lambda_w(axes: Any, weights: Any) -> float:
    """Λ_w(x) in [0, 1]; exactly 0.0 iff some axis is 0. Raises LambdaContractError."""
    log_lam = log_lambda_w(axes, weights)
    if log_lam == -math.inf:
        return 0.0
    return math.exp(log_lam)


def check_tau(tau: Any) -> float:
    """tau as a float if it is real, finite and in (0, 1]; else LAMBDA_TAU_INVALID."""
    if not _is_real(tau):
        raise LambdaContractError(TAU_INVALID, f"tau is {type(tau).__name__}, not a real number")
    if _is_nonfinite(tau):
        raise LambdaContractError(TAU_INVALID, f"tau={tau!r} is not finite")
    if not 0 < tau <= 1:
        raise LambdaContractError(TAU_INVALID, f"tau={tau!r} is outside (0, 1]")
    return float(tau)


def compare_log(log_value: float, log_tau: float) -> str:
    """ABOVE, BELOW or TIE for log Λ against log tau, with the TIE_EPS band.

    -inf (a zero axis) is BELOW. A NaN input is never ABOVE: it compares as TIE,
    so it fails closed.
    """
    if log_value == -math.inf:
        return BELOW
    delta = log_value - log_tau
    if abs(delta) <= TIE_EPS or delta != delta:
        return TIE
    return ABOVE if delta > 0 else BELOW


def gate_v1(axes: Any, weights: Any, tau: Any) -> Tuple[str, Optional[str]]:
    """(verdict, code) for Λ_w(axes) against tau, exactly as the reference. Never raises."""
    try:
        t = check_tau(tau)
        log_lam = log_lambda_w(axes, weights)
    except LambdaContractError as err:
        return BLOCK, err.code
    if log_lam == -math.inf:
        return NO_GO, ZERO_VETO
    outcome = compare_log(log_lam, math.log(t))
    if outcome == TIE:
        return ABSTAIN, NUMERIC_TIE
    if outcome == ABOVE:
        return GO, None
    return NO_GO, BELOW_TAU


class LogAccumulator:
    """Incremental (S, Z) over one endpoint vector (INVENTION §2.10).

    S is the fsum of w · log x over the axes added so far with x > 0, and Z is
    the number of zero axes. An axis not yet added counts as x = 1 (log 1 = 0),
    which is the upper end of a pending seat. Used only for early tests; the
    final decision is always recomputed from scratch.
    """

    __slots__ = ("_terms", "_zeros", "_keys")

    def __init__(self) -> None:
        self._terms: list[float] = []
        self._zeros = 0
        self._keys: set[str] = set()

    def add(self, key: str, x: Any, w: Any) -> None:
        """Add one axis value x with weight w. Raises LambdaContractError or ValueError."""
        if not _is_real(x):
            raise LambdaContractError(TYPE_INVALID, f"axis is {type(x).__name__}")
        if not _is_real(w):
            raise LambdaContractError(TYPE_INVALID, f"weight is {type(w).__name__}")
        if _is_nonfinite(x):
            raise LambdaContractError(NONFINITE_AXIS, f"axis={x!r}")
        if not 0 <= x <= 1:
            raise LambdaContractError(AXIS_OUT_OF_RANGE, f"axis={x!r} is outside [0, 1]")
        if _is_nonfinite(w):
            raise LambdaContractError(NONFINITE_WEIGHT, f"weight={w!r}")
        if not w > 0:
            raise LambdaContractError(WEIGHT_NONPOSITIVE, f"weight={w!r} is not > 0")
        if key in self._keys:
            raise ValueError(f"axis {key!r} added twice")
        self._keys.add(key)
        if x == 0:
            self._zeros += 1
        else:
            self._terms.append(float(w) * math.log(float(x)))

    @property
    def zeros(self) -> int:
        return self._zeros

    def log_value(self) -> float:
        """log Λ with every pending axis at 1: -inf if Z > 0, else fsum of the terms."""
        if self._zeros:
            return -math.inf
        return math.fsum(self._terms)
