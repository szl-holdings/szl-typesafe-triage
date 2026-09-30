# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""The gate: per-seat hard floors AND interval-Lambda (INVENTION §2.2-§2.3).

PT-G1..G6 from the design, plus fail-closed by type (I1): a missing, NaN,
+-Inf, forged or bottom mandatory reading never yields GO.
"""
from __future__ import annotations

import itertools
import math

import pytest

from szl_decide import gate as gate_mod
from szl_decide import lam
from szl_decide.gate import (GateResult, Policy, PolicyError, ReasonClass, Seat, SeatReading,
                             binding_stage, failing_set, floored, gate)
from szl_decide.lattice import BOTTOM, GO_I, NO_GO_I, Interval, Tri, corner, from_tri

from . import _gen


def make_seats(floors, weights, calibrated=()):
    return tuple(
        Seat(id=f"s{k}", scope="test", floor=f, weight=w, owner="owner-test", version="1",
             reads=frozenset({f"res:{k}"}), cost_class="FREE_DETERMINISTIC",
             calibrated=k in calibrated)
        for k, (f, w) in enumerate(zip(floors, weights)))


def make_policy(floors, weights, tau, **kw):
    return Policy(seats=make_seats(floors, weights, kw.pop("calibrated", ())), tau=tau,
                  policy_rev="rev-test", lambda_impl_sha="sha-test", tau_source="test", **kw)


def reading(seat, interval, code="OK", cls=ReasonClass.NONE):
    return SeatReading(seat=seat, interval=interval, reason_code=code, reason_class=cls)


def readings_of(intervals):
    return {f"s{k}": reading(f"s{k}", i) for k, i in enumerate(intervals)}


def forge(cls, **fields):
    """Build an instance without running its validation, as a hostile caller could."""
    obj = object.__new__(cls)
    for name, value in fields.items():
        object.__setattr__(obj, name, value)
    return obj


def random_case(r, k=None):
    k = k or r.randint(1, 6)
    return _gen.floors(r, k), _gen.weights(r, k), _gen.tau(r)


# ------------------------------------------------------------- floored() --

def test_floored_zeroes_each_endpoint_below_the_floor():
    assert floored(Interval(0.3, 0.9), 0.5) == Interval(0.0, 0.9)
    assert floored(Interval(0.6, 0.9), 0.5) == Interval(0.6, 0.9)
    assert floored(Interval(0.1, 0.4), 0.5) == NO_GO_I
    assert floored(Interval(0.5, 0.5), 0.5) == Interval(0.5, 0.5)
    assert floored(BOTTOM, 1.0) == BOTTOM
    assert floored(GO_I, 1.0) == GO_I


def test_floored_is_monotone_in_both_orders():
    r = _gen.rng(20)
    for i in range(_gen.CASES):
        f = r.uniform(0.01, 1.0)
        a = _gen.interval(r)
        b = _gen.refine(r, a)
        fa, fb = floored(a, f), floored(b, f)
        assert fa.lo <= fb.lo and fb.hi <= fa.hi, i  # information order kept
        c = _gen.raise_endpoints(r, a)
        fc = floored(c, f)
        assert fa.lo <= fc.lo and fa.hi <= fc.hi, i  # truth order kept


# ------------------------------------------------------------------ PT-G1 --

KLEENE_TAUS = (5e-324, 1e-300, 1e-9, 0.1, 0.5, 0.65, 0.8, 0.99)


def test_pt_g1_gate_is_kleene_min_on_all_corners():
    r = _gen.rng(21)
    for k in range(1, 7):
        for combo in itertools.product(Tri, repeat=k):
            fl = _gen.floors(r, k)
            ws = _gen.weights(r, k)
            t = r.choice(KLEENE_TAUS)
            res = gate(readings_of([from_tri(c) for c in combo]), make_policy(fl, ws, t))
            assert res.verdict is min(combo), (combo, fl, ws, t)


def test_all_go_at_tau_one_is_a_numeric_tie_not_a_pass():
    # The tie band also covers the ceiling: Lambda = 1 against tau = 1 is a tie.
    # This matches the reference (vector tau_one and FF-01 review note 1).
    res = gate(readings_of([GO_I, GO_I]), make_policy([0.5, 0.5], [0.5, 0.5], 1.0))
    assert (res.verdict, res.code) == (Tri.ABSTAIN, gate_mod.NUMERIC_TIE)


# ------------------------------------------------------------------ PT-G2 --

def test_pt_g2_seat_below_its_floor_is_no_go_for_every_tau():
    # 2,000 random configurations x 10 tau values = 20,000 (configuration, tau) cases.
    r = _gen.rng(22)
    for i in range(_gen.CASES // 5):
        fl, ws, _ = random_case(r)
        k = len(fl)
        ivs = [_gen.interval(r) for _ in range(k)]
        j = r.randrange(k)
        hi = r.uniform(0.0, fl[j]) if fl[j] > 0 else 0.0
        if hi >= fl[j]:
            hi = 0.0
        ivs[j] = Interval(r.uniform(0.0, hi), hi)
        for t in _gen.TAU_GRID + (r.uniform(1e-6, 1.0),):
            res = gate(readings_of(ivs), make_policy(fl, ws, t))
            assert res.verdict is Tri.NO_GO, (i, t)
            assert res.code == gate_mod.VETO, (i, t)
            assert res.lambda_hi == 0.0, (i, t)


def test_veto_holds_even_when_every_other_seat_is_go_and_weight_is_tiny():
    ws = [1e-6, 1 - 1e-6]
    for t in _gen.TAU_GRID:
        res = gate(readings_of([Interval(0.79, 0.79), GO_I]), make_policy([0.8, 0.5], ws, t))
        assert res.verdict is Tri.NO_GO and res.code == gate_mod.VETO


# ------------------------------------------------------------------ PT-G3 --

def _floor_screen(x, f):
    return all(a >= b for a, b in zip(x, f))


def test_pt_g3_no_floor_free_lambda_gate_equals_the_floor_screen():
    # Theorem 2.5 as a search: for K >= 2 and f in (0,1), every (w, tau) has a point
    # where the pure soft gate and the floor screen disagree. Candidates follow the
    # proof: x = f, and (x_j, 1, ..., 1) with x_j just under f_j.
    r = _gen.rng(23)
    band = math.exp(2 * lam.TIE_EPS)
    for i in range(_gen.CASES):
        k = r.randint(2, 6)
        f = [r.uniform(0.01, 0.99) for _ in range(k)]
        ws = _gen.weights(r, k)
        t = r.uniform(1e-6, 0.999)
        candidates = [list(f)]
        for j in range(k):
            thr = (t * band) ** (1.0 / ws[j])
            if f[j] > thr:
                x = [1.0] * k
                x[j] = (f[j] + thr) / 2.0
                candidates.append(x)
        separated = [x for x in candidates
                     if _floor_screen(x, f) != (lam.gate_v1(x, ws, t)[0] == "GO")]
        assert separated, (i, f, ws, t)
        # The hybrid gate (floors AND Lambda) refuses every separating point that
        # fails the floor screen, which the pure soft gate admitted.
        pol = make_policy(f, ws, t)
        for x in separated:
            res = gate(readings_of([Interval(v, v) for v in x]), pol)
            if not _floor_screen(x, f):
                assert res.verdict is Tri.NO_GO, (i, x)


def test_hybrid_gate_on_points_equals_soft_gate_on_the_floored_point():
    r = _gen.rng(24)
    names = {"GO": Tri.GO, "NO_GO": Tri.NO_GO, "ABSTAIN": Tri.ABSTAIN}
    for i in range(_gen.CASES):
        fl, ws, t = random_case(r)
        x = [r.random() for _ in fl]
        xt = [v if v >= f else 0.0 for v, f in zip(x, fl)]
        res = gate(readings_of([Interval(v, v) for v in x]), make_policy(fl, ws, t))
        assert res.verdict is names[lam.gate_v1(xt, ws, t)[0]], i


# ------------------------------------------------------------------ PT-G4 --

def test_pt_g4_refinement_never_flips_go_and_no_go():
    r = _gen.rng(25)
    for i in range(_gen.CASES):
        fl, ws, t = random_case(r)
        pol = make_policy(fl, ws, t)
        old = [_gen.interval(r) for _ in fl]
        new = [_gen.refine(r, iv) for iv in old]
        v_old = gate(readings_of(old), pol).verdict
        v_new = gate(readings_of(new), pol).verdict
        if v_old is Tri.GO:
            assert v_new is Tri.GO, i
        if v_old is Tri.NO_GO:
            assert v_new is Tri.NO_GO, i


def test_pt_g4_raising_endpoints_never_lowers_the_verdict():
    r = _gen.rng(26)
    for i in range(_gen.CASES):
        fl, ws, t = random_case(r)
        pol = make_policy(fl, ws, t)
        low = [_gen.interval(r) for _ in fl]
        high = [_gen.raise_endpoints(r, iv) for iv in low]
        assert gate(readings_of(low), pol).verdict <= gate(readings_of(high), pol).verdict, i


# ------------------------------------------------------------------ PT-G5 --

def test_pt_g5_go_is_sound_over_the_whole_box():
    r = _gen.rng(27)
    seen_go = 0
    for i in range(_gen.CASES):
        fl, ws, t = random_case(r)
        ivs = []
        for f in fl:
            lo = r.uniform(f, 1.0)
            ivs.append(Interval(lo, r.uniform(lo, 1.0)) if r.random() < 0.8 else _gen.interval(r))
        res = gate(readings_of(ivs), make_policy(fl, ws, t))
        if res.verdict is not Tri.GO:
            continue
        seen_go += 1
        for _ in range(8):
            x = [_gen.point_in(r, iv) for iv in ivs]
            assert _floor_screen(x, fl), i
            assert lam.gate_v1(x, ws, t)[0] == "GO", i
    assert seen_go > 1_000


# ------------------------------------------------------------------ PT-G6 --

TIE_CASES = [
    # (axis, tau, verdict, code): the FF-01 tie-band vectors, as point intervals.
    (0.8, 0.8, Tri.ABSTAIN, "NUMERIC_TIE"),
    (0.8000000004000001, 0.8, Tri.ABSTAIN, "NUMERIC_TIE"),
    (0.7999999996, 0.8, Tri.ABSTAIN, "NUMERIC_TIE"),
    (0.8000000016, 0.8, Tri.GO, "OK"),
    (0.7999999984, 0.8, Tri.NO_GO, "BELOW_TAU"),
    (0.649951, 0.65, Tri.NO_GO, "BELOW_TAU"),  # E5: round(.., 4) would pass it
]


@pytest.mark.parametrize("axis, tau, verdict, code", TIE_CASES)
def test_pt_g6_tie_band_is_one_e_minus_nine_in_log_space(axis, tau, verdict, code):
    res = gate(readings_of([Interval(axis, axis)]), make_policy([0.01], [1.0], tau))
    assert (res.verdict, res.code) == (verdict, code)


def test_tie_on_either_endpoint_abstains():
    pol = make_policy([0.01], [1.0], 0.8)
    assert gate(readings_of([Interval(0.8, 0.95)]), pol).code == gate_mod.NUMERIC_TIE
    assert gate(readings_of([Interval(0.5, 0.8)]), pol).code == gate_mod.NUMERIC_TIE
    res = gate(readings_of([Interval(0.5, 0.95)]), pol)
    assert (res.verdict, res.code) == (Tri.ABSTAIN, gate_mod.UNDETERMINED)


def test_band_matches_the_scalar_reference_on_points():
    r = _gen.rng(28)
    for i in range(_gen.CASES):
        t = r.uniform(0.01, 1.0)
        x = min(1.0, t * math.exp(r.uniform(-3e-9, 3e-9)))
        res = gate(readings_of([Interval(x, x)]), make_policy([1e-3], [1.0], t))
        expected = lam.gate_v1([x], [1.0], t)
        assert res.verdict.name == expected[0], i
        assert res.code == (expected[1] or "OK"), i


# --------------------------------------------- binding_stage (Lemma 2.6) --

def test_binding_stage_is_floors_only_when_tau_is_clearly_at_or_below_the_floor_product():
    assert binding_stage(make_policy([0.8] * 4, [0.25] * 4, 0.5)) == "floors"
    assert binding_stage(make_policy([0.8] * 4, [0.25] * 4, 0.9)) == "lambda"
    # Exactly at the floor product: an all-at-floor reading is a tie, so Lambda binds.
    assert binding_stage(make_policy([0.8] * 4, [0.25] * 4, 0.8)) == "lambda"


def test_binding_stage_floors_means_every_survivor_is_go():
    r = _gen.rng(29)
    for i in range(_gen.CASES // 2):
        fl, ws, t = random_case(r)
        pol = make_policy(fl, ws, t)
        at_floor = gate(readings_of([Interval(f, f) for f in fl]), pol).verdict
        if binding_stage(pol) == "floors":
            assert at_floor is Tri.GO, i
            ivs = [Interval(lo, r.uniform(lo, 1.0)) for lo in (r.uniform(f, 1.0) for f in fl)]
            assert gate(readings_of(ivs), pol).verdict is Tri.GO, i
        else:
            assert at_floor is not Tri.GO, i


# ------------------------------------------------------------ failing_set --

def test_failing_set_names_vetoing_and_abstaining_seats_in_policy_order():
    pol = make_policy([0.5, 0.5, 0.5, 0.5], [0.25] * 4, 0.1)
    rs = {
        "s0": reading("s0", Interval(0.1, 0.4), "LOW"),
        "s1": reading("s1", Interval(0.2, 0.9), "WIDE"),
        "s2": reading("s2", GO_I),
    }
    assert failing_set(rs, pol) == (
        ("s0", "VETO", "LOW"), ("s1", "ABSTAIN", "WIDE"), ("s3", "ABSTAIN", "MISSING_READING"))


# ---------------------------------------------- I1: fail closed by type --

def _corruptions(seat_id):
    yield "missing", None
    yield "bottom", reading(seat_id, BOTTOM)
    for label, lo, hi in [("nan_lo", math.nan, 1.0), ("nan_hi", 1.0, math.nan),
                          ("nan_both", math.nan, math.nan), ("pinf", math.inf, math.inf),
                          ("ninf", -math.inf, 1.0), ("pinf_hi", 1.0, math.inf),
                          ("inverted", 1.0, 0.5), ("above_one", 1.5, 1.5),
                          ("bool", True, True), ("none", None, None), ("str", "1", "1")]:
        yield label, forge(SeatReading, seat=seat_id, interval=forge(Interval, lo=lo, hi=hi),
                           reason_code="OK", reason_class=ReasonClass.NONE, evidence_digests=(),
                           missing_slots=(), score_f64=None)
    yield "not_an_interval", forge(SeatReading, seat=seat_id, interval=(1.0, 1.0),
                                   reason_code="OK", reason_class=ReasonClass.NONE,
                                   evidence_digests=(), missing_slots=(), score_f64=None)
    yield "wrong_seat", reading("someone-else", GO_I)
    yield "bare_float", 1.0
    yield "bare_tri", Tri.GO
    yield "dict", {"seat": seat_id, "interval": [1.0, 1.0]}
    yield "none_value", "NONE"


def test_i1_no_corrupted_mandatory_reading_ever_yields_go():
    r = _gen.rng(30)
    for i in range(2_000):
        k = r.randint(1, 6)
        fl, ws = _gen.floors(r, k), _gen.weights(r, k)
        t = r.uniform(1e-6, 0.99)
        pol = make_policy(fl, ws, t)
        base = readings_of([GO_I] * k)
        assert gate(base, pol).verdict is Tri.GO, i
        j = r.randrange(k)
        for label, bad in _corruptions(f"s{j}"):
            rs = dict(base)
            if bad is None:
                del rs[f"s{j}"]
            else:
                rs[f"s{j}"] = bad  # type: ignore[assignment]
            res = gate(rs, pol)
            assert res.verdict is not Tri.GO, (i, label)
            if label == "missing":
                assert res.code == gate_mod.MISSING_READING
            elif label not in ("bottom",):
                assert res.code == gate_mod.INVALID_READING, (i, label, res.code)


def test_seat_reading_refuses_invalid_fields_at_construction():
    for kwargs in [dict(seat="", interval=GO_I), dict(seat=1, interval=GO_I),
                   dict(seat="s0", interval=(1.0, 1.0)), dict(seat="s0", interval=1.0),
                   dict(seat="s0", interval=forge(Interval, lo=math.nan, hi=1.0))]:
        with pytest.raises((TypeError, ValueError)):
            SeatReading(reason_code="OK", reason_class=ReasonClass.NONE, **kwargs)
    with pytest.raises((TypeError, ValueError)):
        SeatReading(seat="s0", interval=GO_I, reason_code="OK", reason_class="NONE")
    with pytest.raises((TypeError, ValueError)):
        SeatReading(seat="s0", interval=GO_I, reason_code="OK", reason_class=ReasonClass.NONE,
                    score_f64=0.9)
    ok = SeatReading(seat="s0", interval=GO_I, reason_code="OK", reason_class=ReasonClass.NONE,
                     score_f64="f64:3feccccccccccccd")
    assert ok.score_f64 == "f64:3feccccccccccccd"


def test_veto_still_wins_over_a_missing_reading():
    pol = make_policy([0.5, 0.5], [0.5, 0.5], 0.5)
    res = gate({"s0": reading("s0", NO_GO_I)}, pol)
    assert (res.verdict, res.code) == (Tri.NO_GO, gate_mod.VETO)


def test_missing_seats_cannot_rescue_a_below_tau_upper_bound():
    # Pending seats sit at [0, 1]; if the upper bound is already below tau, NO_GO.
    pol = make_policy([0.01, 0.01], [0.5, 0.5], 0.8)
    res = gate({"s0": reading("s0", Interval(0.2, 0.3))}, pol)
    assert (res.verdict, res.code) == (Tri.NO_GO, gate_mod.BELOW_TAU)


def test_unexpected_extra_reading_caps_the_verdict_below_go():
    pol = make_policy([0.5], [1.0], 0.5)
    rs = readings_of([GO_I])
    rs["intruder"] = reading("intruder", GO_I)
    res = gate(rs, pol)
    assert (res.verdict, res.code) == (Tri.ABSTAIN, gate_mod.UNEXPECTED_READING)
    rs["s0"] = reading("s0", NO_GO_I)
    assert gate(rs, pol).verdict is Tri.NO_GO


def test_readings_that_are_not_a_mapping_never_pass():
    pol = make_policy([0.5], [1.0], 0.5)
    for bad in (None, [reading("s0", GO_I)], "s0", 1.0, {1: reading("s0", GO_I)}):
        res = gate(bad, pol)  # type: ignore[arg-type]
        assert res.verdict is not Tri.GO


# ------------------------------------------------------------------ Policy --

def test_policy_carries_alpha_council_bound_defaulting_to_none():
    pol = make_policy([0.5], [1.0], 0.5)
    assert pol.alpha_council_bound is None
    assert "alpha_council_bound" in Policy.__dataclass_fields__
    field = Policy.__dataclass_fields__["alpha_council_bound"]
    assert field.default is None
    cal = make_policy([0.5, 0.5], [0.5, 0.5], 0.5, calibrated=(0, 1), alpha_council_bound=0.1)
    assert cal.alpha_council_bound == 0.1


@pytest.mark.parametrize("bad", [math.nan, math.inf, -0.01, True, "0.1"])
def test_alpha_council_bound_must_be_a_finite_non_negative_number(bad):
    with pytest.raises(PolicyError):
        make_policy([0.5], [1.0], 0.5, calibrated=(0,), alpha_council_bound=bad)


def test_alpha_council_bound_needs_a_calibrated_seat():
    with pytest.raises(PolicyError):
        make_policy([0.5], [1.0], 0.5, alpha_council_bound=0.05)


@pytest.mark.parametrize("floors, weights, tau, code", [
    ([0.5], [1.0], 0.0, "LAMBDA_TAU_INVALID"),
    ([0.5], [1.0], math.nan, "LAMBDA_TAU_INVALID"),
    ([0.5], [1.0], 1.5, "LAMBDA_TAU_INVALID"),
    ([0.5], [1.0], None, "LAMBDA_TAU_INVALID"),
    ([0.5, 0.5], [0.5, 0.6], 0.5, "LAMBDA_WEIGHT_SUM"),
    ([0.5, 0.5], [1.5, -0.5], 0.5, "SEAT_INVALID"),
    ([0.5, 0.5], [1.0, 0.0], 0.5, "SEAT_INVALID"),
    ([0.0], [1.0], 0.5, "SEAT_INVALID"),
    ([1.01], [1.0], 0.5, "SEAT_INVALID"),
    ([math.nan], [1.0], 0.5, "SEAT_INVALID"),
    ([True], [1.0], 0.5, "SEAT_INVALID"),
])
def test_invalid_policy_is_refused_with_a_code(floors, weights, tau, code):
    with pytest.raises(PolicyError) as info:
        make_policy(floors, weights, tau)
    assert info.value.code == code


def test_policy_refuses_empty_and_duplicate_seats():
    with pytest.raises(PolicyError) as info:
        Policy(seats=(), tau=0.5, policy_rev="r", lambda_impl_sha="s", tau_source="t")
    assert info.value.code == "POLICY_SEATS_INVALID"
    seat = make_seats([0.5], [0.5])[0]
    with pytest.raises(PolicyError) as info:
        Policy(seats=(seat, seat), tau=0.5, policy_rev="r", lambda_impl_sha="s", tau_source="t")
    assert info.value.code == "POLICY_SEAT_DUPLICATE"


def test_seat_refuses_an_unknown_cost_class():
    with pytest.raises(PolicyError):
        Seat(id="s", scope="x", floor=0.5, weight=1.0, owner="o", version="1",
             reads=frozenset(), cost_class="FREE")


def test_forged_invalid_policy_never_passes():
    good = make_policy([0.5], [1.0], 0.5)
    rs = readings_of([GO_I])
    assert gate(rs, good).verdict is Tri.GO
    for field, value in [("tau", 0.0), ("tau", math.nan), ("seats", ())]:
        bad = forge(Policy, **{**{f: getattr(good, f) for f in Policy.__dataclass_fields__},
                               field: value})
        res = gate(rs, bad)
        assert res.verdict is Tri.ABSTAIN and res.lambda_lo is None, field
    assert gate(rs, "policy").verdict is Tri.ABSTAIN  # type: ignore[arg-type]


def test_gate_result_reports_both_lambda_endpoints():
    pol = make_policy([0.1, 0.1], [0.5, 0.5], 0.5)
    res = gate(readings_of([Interval(0.64, 0.81), GO_I]), pol)
    assert isinstance(res, GateResult)
    assert res.lambda_lo == lam.lambda_w([0.64, 1.0], [0.5, 0.5])
    assert res.lambda_hi == lam.lambda_w([0.81, 1.0], [0.5, 0.5])
    assert res.log_lo == lam.log_lambda_w([0.64, 1.0], [0.5, 0.5])
    assert res.verdict is Tri.GO and res.code == "OK"


def test_reason_class_has_the_seven_documented_members():
    assert [m.value for m in ReasonClass] == [
        "NONE", "VETO", "EVIDENCE_INSUFFICIENT", "IN_BAND", "POLICY_HOLD", "UNKNOWN", "SYSTEM"]
    assert gate_mod.COST_CLASSES == ("FREE_DETERMINISTIC", "PAID", "VOLATILE_FETCH")


def test_corner_of_a_gate_input_is_unchanged_by_floors():
    for t in Tri:
        assert corner(floored(from_tri(t), 0.7)) is t
