# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""The non-compensatory property is the load-bearing claim. Test it hardest."""
import math

import pytest

from szl_triage import lambda_aggregate

W = {"a": 1.0, "b": 1.0, "c": 1.0, "d": 1.0}


def test_all_ones_is_one():
    assert lambda_aggregate({"a": 1.0, "b": 1.0}, W) == 1.0


def test_single_zero_zeroes_everything():
    assert lambda_aggregate({"a": 1.0, "b": 1.0, "c": 0.0}, W) == 0.0


def test_zero_cannot_be_outvoted_by_many_ones():
    assert lambda_aggregate({"a": 1.0, "b": 1.0, "c": 1.0, "d": 0.0}, W) == 0.0


def test_epsilon_treated_as_zero():
    assert lambda_aggregate({"a": 1e-15, "b": 1.0}, W) == 0.0


def test_equal_weights_match_geometric_mean():
    got = lambda_aggregate({"a": 0.25, "b": 1.0}, W)
    assert got == pytest.approx(math.sqrt(0.25), abs=1e-4)


def test_weighting_shifts_result_toward_heavier_axis():
    heavy = lambda_aggregate({"a": 0.2, "b": 1.0}, {"a": 9.0, "b": 1.0})
    light = lambda_aggregate({"a": 0.2, "b": 1.0}, {"a": 1.0, "b": 9.0})
    assert heavy < light


def test_empty_axes_is_zero():
    assert lambda_aggregate({}, W) == 0.0


def test_values_above_one_are_clamped():
    assert lambda_aggregate({"a": 5.0, "b": 1.0}, W) == 1.0


def test_negative_values_clamp_to_zero_and_zero_result():
    assert lambda_aggregate({"a": -3.0, "b": 1.0}, W) == 0.0


def test_missing_weight_raises_rather_than_defaulting():
    with pytest.raises(KeyError):
        lambda_aggregate({"unweighted": 0.5}, {"a": 1.0})


def test_nonpositive_total_weight_is_zero():
    assert lambda_aggregate({"a": 0.5}, {"a": 0.0}) == 0.0


def test_result_is_deterministic():
    axes = {"a": 0.37, "b": 0.82, "c": 0.5}
    assert lambda_aggregate(axes, W) == lambda_aggregate(axes, W)
