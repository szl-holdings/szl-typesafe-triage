# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Pinned divergence: today's szl_triage behaviour, stated exactly, beside what the
szl.lambda/v1 contract in szl_decide says for the same input.

These are not expected failures. Each row asserts today's value exactly, so any
silent change in `szl_triage` fails here. The slice that changes the behaviour
(EN-10, owner-gated) edits KNOWN_DIVERGENCE in the same PR, and the reason is
visible in review. Keyed by the FUSION_BRIEF E-id.

Anchors (origin/main 77d96a2): `src/szl_triage/aggregate.py:46-58` renormalises
over the present axes and clamps, with `round(..., 4)` at :58, and
`engine.py` compares `aggregate >= policy.lambda_threshold`;
`src/szl_triage/providers/systemone.py:101-107` makes `noul_to_integrity` return
1.0 on a missing answer or a schema violation.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from szl_decide import lam
from szl_decide.gate import Policy, ReasonClass, Seat, SeatReading, gate
from szl_decide.lattice import BOTTOM, Interval, Tri
from szl_triage.aggregate import lambda_aggregate
from szl_triage.providers.systemone import noul_to_integrity

ROOT = Path(__file__).resolve().parents[2]
V3 = json.loads((ROOT / "src" / "szl_triage" / "data" / "triage_policy.v3.json")
                .read_text(encoding="utf-8"))
W3 = V3["axis_weights"]          # lexical .25, breadth .4, integrity .2, separation .15
ORDER = ("lexical", "breadth", "integrity", "separation")

#: id -> (triage axes, triage weights, today's aggregate, v1 axes, v1 weights, v1 outcome).
#: A v1 outcome is ("value", float) or ("error", code). Values are exact.
KNOWN_DIVERGENCE = {
    "E5.renormalise_dropped_axis": (
        {"lexical": 0.8485, "breadth": 0.8485, "separation": 0.8485}, W3, 0.8485,
        [0.8485, 0.8485, 0.8485], [W3[a] for a in ORDER], ("error", "LAMBDA_LENGTH_MISMATCH")),
    "E5.present_axis_reference": (
        {"lexical": 0.8485, "breadth": 0.8485, "integrity": 0.1, "separation": 0.8485}, W3, 0.5533,
        [0.8485, 0.8485, 0.1, 0.8485], [W3[a] for a in ORDER], ("value", 0.5532500697127598)),
    "E5.round_4dp_before_compare": (
        {"x": 0.649951}, {"x": 1.0}, 0.65,
        [0.649951], [1.0], ("value", 0.649951)),
    "E5.clamp_above_one": (
        {"a": 1.5, "b": 0.9}, {"a": 0.5, "b": 0.5}, 0.9487,
        [1.5, 0.9], [0.5, 0.5], ("error", "LAMBDA_AXIS_OUT_OF_RANGE")),
    "E5.pos_inf_treated_as_one": (
        {"a": math.inf, "b": 0.9}, {"a": 0.5, "b": 0.5}, 0.9487,
        [math.inf, 0.9], [0.5, 0.5], ("error", "LAMBDA_NONFINITE_AXIS")),
    "E5.negative_clamped_to_zero": (
        {"a": -0.1, "b": 0.9}, {"a": 0.5, "b": 0.5}, 0.0,
        [-0.1, 0.9], [0.5, 0.5], ("error", "LAMBDA_AXIS_OUT_OF_RANGE")),
    "E5.unnormalised_weights_renormalised": (
        {"a": 0.81, "b": 0.64}, {"a": 2.0, "b": 2.0}, 0.72,
        [0.81, 0.64], [2.0, 2.0], ("error", "LAMBDA_WEIGHT_SUM")),
    "E5.empty_is_zero": (
        {}, {}, 0.0,
        [], [], ("error", "LAMBDA_EMPTY")),
}

#: noul_to_integrity inputs -> today's integrity value (E4f). The engine contract
#: maps each of these to bottom [0, 1] (ABSTAIN), never to a clean 1.0.
KNOWN_NOUL_DIVERGENCE = {
    "E4f.value_none": ({"value": None}, 1.0),
    "E4f.value_missing": ({}, 1.0),
    "E4f.schema_violation": ({"schema_violation": "probability outside [0,1]", "value": 0.9}, 1.0),
    "E4f.value_nan": ({"value": math.nan}, 1.0),
}


@pytest.mark.parametrize("eid", sorted(KNOWN_DIVERGENCE))
def test_today_aggregate_value_is_pinned_exactly(eid):
    axes, weights, today, *_ = KNOWN_DIVERGENCE[eid]
    got = lambda_aggregate(axes, weights)
    assert got == today, f"{eid}: szl_triage changed ({got!r}); update KNOWN_DIVERGENCE in EN-10"


@pytest.mark.parametrize("eid", sorted(KNOWN_DIVERGENCE))
def test_v1_contract_outcome_for_the_same_input(eid):
    *_, v1_axes, v1_weights, (kind, want) = KNOWN_DIVERGENCE[eid]
    if kind == "error":
        with pytest.raises(lam.LambdaContractError) as info:
            lam.lambda_w(v1_axes, v1_weights)
        assert info.value.code == want
    else:
        assert lam.lambda_w(v1_axes, v1_weights) == want


def test_the_rows_really_diverge():
    for eid, (axes, weights, today, v1_axes, v1_weights, (kind, want)) in KNOWN_DIVERGENCE.items():
        if eid == "E5.present_axis_reference":
            continue  # the baseline for the dropped-axis row, not a divergence by itself
        assert kind == "error" or want != today, eid


def test_rounding_turns_a_refusal_into_a_measured_pass_at_triage_tau():
    # engine.py admits when aggregate >= lambda_threshold. v1 compares unrounded, in
    # log space, and refuses.
    assert lambda_aggregate({"x": 0.649951}, {"x": 1.0}) >= 0.65
    assert lam.gate_v1([0.649951], [1.0], 0.65) == ("NO_GO", "BELOW_TAU")
    assert V3["lambda_threshold"] == 0.65


def test_dropping_the_integrity_axis_raises_the_triage_score():
    kept = KNOWN_DIVERGENCE["E5.present_axis_reference"][2]
    dropped = KNOWN_DIVERGENCE["E5.renormalise_dropped_axis"][2]
    assert (kept, dropped) == (0.5533, 0.8485)
    assert kept < V3["lambda_threshold"] <= dropped


def test_nan_axis_today_yields_nan_not_a_refusal_code():
    got = lambda_aggregate({"a": math.nan, "b": 0.9}, {"a": 0.5, "b": 0.5})
    assert math.isnan(got)
    assert not got >= V3["lambda_threshold"]  # it falls to REVIEW only because NaN compares false
    assert lam.gate_v1([math.nan, 0.9], [0.5, 0.5], 0.65) == ("BLOCK", "LAMBDA_NONFINITE_AXIS")


@pytest.mark.parametrize("eid", sorted(KNOWN_NOUL_DIVERGENCE))
def test_today_noul_to_integrity_value_is_pinned_exactly(eid):
    answer, today = KNOWN_NOUL_DIVERGENCE[eid]
    got = noul_to_integrity(dict(answer))
    assert got == today, f"{eid}: noul_to_integrity changed ({got!r}); update the table in EN-10"


def test_a_clean_integrity_of_one_passes_where_bottom_abstains():
    # The same missing answer, read two ways, through the szl_decide gate with an
    # integrity seat at floor 0.5: today's 1.0 as a point opens the gate; the
    # contract's bottom does not.
    seat = Seat(id="integrity", scope="triage", floor=0.5, weight=1.0, owner="owner-test",
                version="1", reads=frozenset({"answer"}), cost_class="FREE_DETERMINISTIC")
    pol = Policy(seats=(seat,), tau=0.65, policy_rev="rev-test", lambda_impl_sha="sha-test",
                 tau_source="triage_policy.v3.json:lambda_threshold")
    today = noul_to_integrity({"value": None})
    as_point = SeatReading(seat="integrity", interval=Interval(today, today), reason_code="OK",
                           reason_class=ReasonClass.NONE)
    as_bottom = SeatReading(seat="integrity", interval=BOTTOM, reason_code="MISSING",
                            reason_class=ReasonClass.UNKNOWN)
    assert gate({"integrity": as_point}, pol).verdict is Tri.GO
    assert gate({"integrity": as_bottom}, pol).verdict is Tri.ABSTAIN
