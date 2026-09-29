# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Fan-in completeness kappa (INVENTION §2.5): exact multiset identity against the
pre-committed expected set E, reported as missing / extra / dup, and a hard
conjunct of the gate (PT-K1, PT-K2).
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter

import pytest

from szl_decide import gate as gate_mod
from szl_decide.fanin import FanInError, Kappa, expected_digest, fanin_kappa
from szl_decide.gate import gate
from szl_decide.lattice import BOTTOM, GO_I, NO_GO_I, Tri

from . import _gen
from .test_gate import make_policy, readings_of

E5 = ("r0", "r1", "r2", "r3", "r4")


def _independent_digest(ids) -> str:
    return hashlib.sha256(json.dumps(sorted(ids), separators=(",", ":"),
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


# ------------------------------------------------------------------ PT-K1 --

def test_pt_k1_count_equal_but_wrong_multiset_is_refused():
    # r0, r1, r1, r3, r4 has the right count (5) and passes a count check.
    k = fanin_kappa(E5, ["r0", "r1", "r1", "r3", "r4"])
    assert k.ok is False
    assert k.missing == ("r2",)
    assert k.dup == ("r1",)
    assert k.extra == ()
    assert k.interval == NO_GO_I


def test_exact_arrival_in_any_order_is_complete():
    k = fanin_kappa(E5, ["r4", "r2", "r0", "r3", "r1"])
    assert k.ok is True
    assert (k.missing, k.extra, k.dup, k.pending) == ((), (), (), ())
    assert k.interval == GO_I


def test_extra_and_injected_ids_are_reported():
    k = fanin_kappa(E5, ["r0", "r1", "r2", "r3", "r4", "evil"])
    assert (k.ok, k.extra, k.missing, k.dup) == (False, ("evil",), (), ())
    k = fanin_kappa(E5, ["r0", "r1", "r2", "r3", "evil", "evil"])
    assert (k.ok, k.extra, k.missing, k.dup) == (False, ("evil",), ("r4",), ("evil",))


def test_pt_k1_ok_iff_the_multisets_are_equal():
    r = _gen.rng(40)
    pool = [f"r{i}" for i in range(8)] + ["x0", "x1"]
    for i in range(_gen.CASES):
        n = r.randint(1, 6)
        expected = r.sample(pool[:8], n)
        received = [r.choice(pool) for _ in range(r.randint(0, 8))]
        if r.random() < 0.3:
            received = list(expected)
            r.shuffle(received)
        k = fanin_kappa(expected, received)
        want = Counter(received) == Counter(expected)
        assert k.ok is want, (i, expected, received)
        got = Counter(received)
        assert set(k.missing) == set(expected) - set(got), i
        assert set(k.extra) == set(got) - set(expected), i
        assert set(k.dup) == {x for x, c in got.items() if c > 1}, i
        assert list(k.missing) == sorted(k.missing), i


def test_expected_digest_is_order_free_and_matches_an_independent_computation():
    assert expected_digest(E5) == _independent_digest(E5)
    assert expected_digest(reversed(E5)) == expected_digest(E5)
    assert fanin_kappa(E5, E5).E_digest == expected_digest(E5)
    assert len(expected_digest(E5)) == 64


# ------------------------------------------------------ pending vs failed --

def test_pending_predecessor_is_bottom_and_failed_is_no_go():
    waiting = fanin_kappa(E5, ["r0", "r1", "r2"], pending=["r3", "r4"])
    assert waiting.ok is False and waiting.pending == ("r3", "r4")
    assert waiting.interval == BOTTOM
    failed = fanin_kappa(E5, ["r0", "r1", "r2"], pending=["r3"])  # r4 terminally absent
    assert failed.interval == NO_GO_I
    injected = fanin_kappa(E5, ["r0", "r1", "r2", "zz"], pending=["r3", "r4"])
    assert injected.interval == NO_GO_I


@pytest.mark.parametrize("expected, received, pending", [
    ((), [], ()),                        # an empty expected set is a plan error
    (("r0", "r0"), ["r0"], ()),          # E is a set
    (("r0", ""), ["r0"], ()),            # ids are non-empty strings
    (("r0", 1), ["r0"], ()),
    (("r0",), [None], ()),
    (("r0",), [b"r0"], ()),
    (("r0", "r1"), ["r0"], ["r9"]),      # pending must be expected
    (("r0", "r1"), ["r0", "r1"], ["r1"]),  # pending cannot also have arrived
    ("r0", ["r0"], ()),                  # a bare string is not a collection of ids
])
def test_malformed_inputs_raise_instead_of_passing(expected, received, pending):
    with pytest.raises(FanInError):
        fanin_kappa(expected, received, pending=pending)


def test_kappa_refuses_an_inconsistent_construction():
    d = expected_digest(E5)
    with pytest.raises(ValueError):
        Kappa(ok=True, missing=("r2",), extra=(), dup=(), E_digest=d)
    with pytest.raises(ValueError):
        Kappa(ok=False, missing=(), extra=(), dup=(), E_digest=d)
    with pytest.raises(ValueError):
        Kappa(ok=True, missing=(), extra=(), dup=(), E_digest="not-a-digest")
    with pytest.raises(ValueError):
        Kappa(ok=1, missing=(), extra=(), dup=(), E_digest=d)  # type: ignore[arg-type]


# ------------------------------------------------------------------ PT-K2 --

def test_pt_k2_any_incomplete_fan_in_is_never_go_for_any_reading_or_tau():
    r = _gen.rng(41)
    bad = [fanin_kappa(E5, ["r0", "r1", "r1", "r3", "r4"]),
           fanin_kappa(E5, ["r0", "r1", "r2", "r3"]),
           fanin_kappa(E5, list(E5) + ["x"]),
           fanin_kappa(E5, ["r0"], pending=["r1", "r2", "r3", "r4"])]
    good = fanin_kappa(E5, E5)
    for i in range(_gen.CASES):
        k = r.randint(1, 5)
        fl, ws = _gen.floors(r, k), _gen.weights(r, k)
        ivs = [GO_I if r.random() < 0.7 else _gen.interval(r) for _ in range(k)]
        t = _gen.tau(r)
        pol = make_policy(fl, ws, t)
        kappa = r.choice(bad)
        fanins = {"join": kappa, "other": good} if r.random() < 0.5 else {"join": kappa}
        res = gate(readings_of(ivs), pol, fanins=fanins)
        assert res.verdict is not Tri.GO, i
        if kappa.interval == NO_GO_I:
            assert res.verdict is Tri.NO_GO, i


def test_complete_fan_in_is_the_identity_of_the_conjunction():
    pol = make_policy([0.5, 0.5], [0.5, 0.5], 0.5)
    rs = readings_of([GO_I, GO_I])
    plain = gate(rs, pol)
    with_fanin = gate(rs, pol, fanins={"join": fanin_kappa(E5, E5)})
    assert plain == with_fanin
    assert with_fanin.verdict is Tri.GO


def test_fan_in_codes():
    pol = make_policy([0.5], [1.0], 0.5)
    rs = readings_of([GO_I])
    res = gate(rs, pol, fanins={"j": fanin_kappa(E5, ["r0", "r1", "r2", "r3"])})
    assert (res.verdict, res.code) == (Tri.NO_GO, gate_mod.FANIN_INCOMPLETE)
    res = gate(rs, pol, fanins={"j": fanin_kappa(E5, ["r0"], pending=["r1", "r2", "r3", "r4"])})
    assert (res.verdict, res.code) == (Tri.ABSTAIN, gate_mod.FANIN_PENDING)
    # A seat veto keeps its own code under a failed fan-in.
    rs_veto = readings_of([NO_GO_I])
    res = gate(rs_veto, pol, fanins={"j": fanin_kappa(E5, ["r0"])})
    assert (res.verdict, res.code) == (Tri.NO_GO, gate_mod.VETO)


def test_forged_or_foreign_fan_in_values_never_pass():
    pol = make_policy([0.5], [1.0], 0.5)
    rs = readings_of([GO_I])
    forged = object.__new__(Kappa)
    for name, value in dict(ok=True, missing=("r2",), extra=(), dup=(), pending=(),
                            E_digest=expected_digest(E5)).items():
        object.__setattr__(forged, name, value)
    for value in (forged, True, 1, None, GO_I, {"ok": True}):
        res = gate(rs, pol, fanins={"j": value})  # type: ignore[dict-item]
        assert res.verdict is not Tri.GO, value
        assert res.code == gate_mod.FANIN_INVALID, value
    assert gate(rs, pol, fanins=[fanin_kappa(E5, E5)]).verdict is not Tri.GO  # type: ignore[arg-type]


def test_graded_coverage_would_hide_a_missing_node():
    # MB §6.2: one missing of 200 at weight 0.25 moves a graded axis by 0.998748 only.
    # kappa is therefore a hard conjunct, never a Lambda axis.
    assert round((1 - 1 / 200) ** 0.25, 6) == 0.998748
