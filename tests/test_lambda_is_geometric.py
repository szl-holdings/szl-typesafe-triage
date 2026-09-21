"""The engine's aggregator is the Lutar Invariant form: weighted geometric mean over axis
scores in [0,1], zero-pinned, reported rounded to 4 decimals. The precision is derived
in scripts/shadow_fidelity.py from the data, not chosen to make a test pass.
"""
import json
from pathlib import Path

from szl_triage import policy as policy_mod
from szl_triage.pipeline import decide

POL = policy_mod.load("policies/triage_policy.v3.json")
W = dict(POL.axis_weights)
PRECISION = 4
ROWS = [json.loads(l) for l in
        Path("policies/redteam_probes.verified.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]


def _geom(ax):
    p = 1.0
    for k, w in W.items():
        v = ax.get(k, 0.0)
        if v <= 0.0:
            return 0.0
        p *= v ** w
    return p


def test_lambda_is_the_weighted_geometric_mean():
    for r in ROWS:
        d = decide(r["input"], POL)
        ax = {k: float(v) for k, v in dict(d.axes).items()}
        assert round(_geom(ax), PRECISION) == d.lambda_value, r["input"]


def test_lambda_is_not_the_arithmetic_mean():
    """Guards against the error made in this session: a sum fits some rows and not others."""
    diffs = 0
    for r in ROWS:
        d = decide(r["input"], POL)
        ax = {k: float(v) for k, v in dict(d.axes).items()}
        if round(sum(W[k] * ax.get(k, 0.0) for k in W), PRECISION) != d.lambda_value:
            diffs += 1
    assert diffs > 0


def test_weights_sum_to_one():
    assert abs(sum(W.values()) - 1.0) < 1e-12


def test_zero_pinning_holds():
    for r in ROWS:
        d = decide(r["input"], POL)
        ax = {k: float(v) for k, v in dict(d.axes).items()}
        if any(v == 0.0 for v in ax.values()):
            assert d.lambda_value == 0.0, r["input"]


def test_retraction_is_recorded():
    d = json.loads(Path("out/aggregator_shadow.json").read_text(encoding="utf-8"))
    assert d["status"].startswith("RETRACTED")