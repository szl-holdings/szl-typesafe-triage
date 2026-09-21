import json
from pathlib import Path

import pytest

P = Path("out/yuyay_gate_conformance.json")


def _d():
    if not P.exists():
        pytest.skip("yuyay receipt absent")
    d = json.loads(P.read_text(encoding="utf-8-sig"))
    if d.get("state") == "DATASET_UNAVAILABLE":
        pytest.skip("dataset unavailable without HF_TOKEN")
    return d


def test_margin_min_equals_conjunctive():
    a = _d().get("agreement", {})
    if "margin_min" not in a:
        pytest.skip("receipt predates the margin-min correction")
    assert a["margin_min"] == a["conjunctive_and"]


def test_compensation_errors_are_reported():
    d = _d()
    assert d.get("compensation_errors", 0) > 0
    assert d.get("compensation_errors_by_axis")


def test_circularity_is_disclosed():
    assert "distillation fidelity" in _d().get("circularity_warning", "")


def test_misspecified_rule_is_kept_labelled():
    d = _d()
    if "self_correction" not in d:
        pytest.skip("receipt predates the correction")
    assert "nobody proposed" in d["self_correction"]
    assert "uniform_threshold_min_MISSPECIFIED" in d["agreement"]


def test_axis_count_mismatch_is_stated():
    d = _d()
    assert d.get("canonical_axis_count") == 13 and d.get("engine_axis_count") == 4