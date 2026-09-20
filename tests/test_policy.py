# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Policy loading fails closed. A permissive default is worse than a crash."""
import pytest

from szl_triage import PolicyError, load_policy


def test_loads_v3(policy):
    assert policy.version.startswith("3.")


def test_review_excluded_from_classifiable(policy):
    assert "REVIEW" not in policy.classifiable


def test_every_classifiable_label_has_rules(policy):
    for label in policy.classifiable:
        assert policy.rules[label]


def test_missing_key_raises(raw_policy, tmp_policy):
    del raw_policy["lambda_threshold"]
    with pytest.raises(PolicyError, match="missing required keys"):
        load_policy(tmp_policy(raw_policy))


def test_missing_review_sink_raises(raw_policy, tmp_policy):
    raw_policy["labels"] = [l for l in raw_policy["labels"] if l != "REVIEW"]
    with pytest.raises(PolicyError, match="REVIEW"):
        load_policy(tmp_policy(raw_policy))


def test_wrong_axis_set_raises(raw_policy, tmp_policy):
    raw_policy["axis_weights"].pop("breadth")
    with pytest.raises(PolicyError, match="axis_weights"):
        load_policy(tmp_policy(raw_policy))


def test_zero_axis_weight_raises(raw_policy, tmp_policy):
    raw_policy["axis_weights"]["integrity"] = 0.0
    with pytest.raises(PolicyError, match="positive"):
        load_policy(tmp_policy(raw_policy))


def test_threshold_out_of_range_raises(raw_policy, tmp_policy):
    raw_policy["lambda_threshold"] = 1.5
    with pytest.raises(PolicyError, match="out of range"):
        load_policy(tmp_policy(raw_policy))


def test_empty_meta_cues_raises(raw_policy, tmp_policy):
    raw_policy["meta_cues"] = []
    with pytest.raises(PolicyError, match="meta_cues"):
        load_policy(tmp_policy(raw_policy))


def test_rule_for_undeclared_label_raises(raw_policy, tmp_policy):
    raw_policy["rules"]["NOPE"] = [{"term": "x", "weight": 0.5}]
    with pytest.raises(PolicyError, match="undeclared"):
        load_policy(tmp_policy(raw_policy))


def test_weight_out_of_range_raises(raw_policy, tmp_policy):
    raw_policy["rules"]["BUG"][0]["weight"] = 3.0
    with pytest.raises(PolicyError, match="weight out of range"):
        load_policy(tmp_policy(raw_policy))


def test_v2_normalization_mode_is_not_accepted(raw_policy, tmp_policy):
    # v1/v2 normalization modes were removed, not kept as selectable options.
    raw_policy.pop("axis_weights")
    raw_policy["normalization"] = "top1"
    with pytest.raises(PolicyError):
        load_policy(tmp_policy(raw_policy))
