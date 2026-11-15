# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Conformal abstention: exact quantiles, finite-sample bounds, fail-closed.

The tests pin the three properties the guarantee rests on:
  1. the conformal quantile is the exact order statistic (no interpolation),
  2. calibration data insufficient for the requested level refuses to issue,
  3. empirical coverage under an exchangeable null sits at the guaranteed level,
     and the recorded Hoeffding bound is recomputable (tamper-evident).
"""
import copy
import math
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import conformal_abstain as ca  # noqa: E402


def test_quantile_is_exact_order_statistic():
    scores = [0.31, 0.97, 0.12, 0.55, 0.55, 0.88, 0.4, 0.66, 0.23, 0.71]
    q = ca.conformal_quantile(scores, alpha=0.3)
    ordered = sorted(scores)
    k = math.ceil((len(scores) + 1) * 0.7)
    assert q == ordered[k - 1]


def test_quantile_refuses_when_insufficient():
    with pytest.raises(ca.ConformalError, match="insufficient calibration data"):
        ca.conformal_quantile([0.1, 0.2, 0.3], alpha=0.05)


def test_hoeffding_bound_maths():
    emp, n, delta = 0.9, 400, 0.05
    expected = emp - math.sqrt(math.log(1.0 / delta) / (2.0 * n))
    assert ca.hoeffding_lower_bound(emp, n, delta) == pytest.approx(expected)
    with pytest.raises(ca.ConformalError):
        ca.hoeffding_lower_bound(0.9, 0, 0.05)


def _null_rows(rng, n, lo=0.55, hi=0.98):
    rows = []
    for i in range(n):
        lam = rng.uniform(lo, hi)
        rows.append({"input": f"calib-{i}", "label": "BUG", "engine_label": "BUG",
                     "engine_lambda": round(lam, 6)})
    return rows


def test_calibrate_produces_verifiable_policy():
    rng = random.Random(1234)
    policy = ca.calibrate(_null_rows(rng, 200), alpha=0.2, delta=0.05)
    assert policy["schema"] == ca.POLICY_SCHEMA
    assert 0.0 <= policy["tau_conformal"] <= 1.0
    assert policy["n_calibration"] + policy["n_holdout"] == 200
    assert ca.check_policy(policy) == []
    assert "exchangeability" in policy["honesty_condition"]


def test_coverage_under_exchangeable_null():
    """Empirical coverage must sit near the guaranteed level across draws."""
    rng = random.Random(20261115)
    trials, alpha = 60, 0.2
    covered = 0
    for _ in range(trials):
        rows = _null_rows(rng, 220)
        policy = ca.calibrate(rows, alpha=alpha, delta=0.05)
        tau = policy["tau_conformal"]
        # One fresh exchangeable point: lambda ~ U(lo, hi).
        new_lam = rng.uniform(0.55, 0.98)
        if new_lam >= tau:
            covered += 1
    empirical = covered / trials
    # Exact guarantee is 1-alpha on average; allow Monte-Carlo slack.
    assert empirical >= 1 - alpha - 0.12, f"coverage collapsed: {empirical}"


def test_higher_alpha_abstains_more():
    """alpha is the tolerated abstention rate among correct exchangeable rows:
    raising alpha licenses MORE abstention, so the acceptance floor rises."""
    rng = random.Random(7)
    rows = _null_rows(rng, 200)
    tau_tight = ca.calibrate(copy.deepcopy(rows), alpha=0.1, delta=0.05)["tau_conformal"]
    tau_loose = ca.calibrate(copy.deepcopy(rows), alpha=0.4, delta=0.05)["tau_conformal"]
    assert tau_loose >= tau_tight


def test_check_policy_detects_tampering():
    rng = random.Random(99)
    policy = ca.calibrate(_null_rows(rng, 200), alpha=0.2, delta=0.05)
    tampered = copy.deepcopy(policy)
    tampered["empirical_coverage"] = 0.999
    problems = ca.check_policy(tampered)
    assert any("hoeffding bound mismatch" in p for p in problems)

    altered = copy.deepcopy(policy)
    altered["honesty_condition"] = "guaranteed unconditionally"
    assert any("honesty condition" in p for p in ca.check_policy(altered))

    broken = copy.deepcopy(policy)
    broken["tau_conformal"] = 1.5
    assert any("tau_conformal out of" in p for p in ca.check_policy(broken))


def test_calibrate_refuses_tiny_corpus():
    with pytest.raises(ca.ConformalError):
        ca.calibrate(_null_rows(random.Random(1), 4), alpha=0.1, delta=0.05)


def test_apply_is_fail_closed():
    rng = random.Random(5)
    policy = ca.calibrate(_null_rows(rng, 200), alpha=0.2, delta=0.05)
    from szl_triage import load_policy

    engine_policy = load_policy(str(ROOT / "policies" / "triage_policy.v3.json"))
    strict = copy.deepcopy(policy)
    strict["tau_conformal"] = 1.0
    out = ca.apply_policy(strict, "how do i set up the exporter", engine_policy)
    assert out["conformal_verdict"] == "CONFORMAL_ABSTAIN"
    generous = copy.deepcopy(policy)
    generous["tau_conformal"] = 0.0
    out2 = ca.apply_policy(generous, "how do i set up the exporter", engine_policy)
    assert out2["conformal_verdict"] == "MEASURED_GUARANTEED"
    assert "exchangeability" in out2["coverage_claim"] or "coverage" in out2["coverage_claim"]


def test_no_competence_overclaim():
    rng = random.Random(3)
    policy = ca.calibrate(_null_rows(rng, 150), alpha=0.2, delta=0.05)
    assert "no competence claim" in policy["trust_ceiling_relation"]


def test_recompute_axes_path_end_to_end(tmp_path):
    """The production --calibrate --recompute-axes path: _engine_axes output
    must carry the exact keys calibrate() consumes, and calibrate must succeed
    over rows in that shape. Regression guard for the axes/lambda key mismatch
    that silently dropped every recomputed row."""
    from pathlib import Path

    import conformal_abstain as ca
    from szl_triage import load_policy

    engine_policy = load_policy(str(Path(ca.__file__).resolve().parents[1]
                                    / "policies" / "triage_policy.v3.json"))
    texts = [
        "charged twice on invoice INV-2041, want a refund",
        "we were billed after cancelling the subscription",
        "duplicate charge on my card statement this month",
        "the payment was taken twice for one order",
        "finance disputes the invoice total and the receipt",
        "refund requested for the double billing error",
        "my statement shows two identical charges",
        "the invoice amount disagrees with the receipt",
    ]
    rows = []
    for t in texts * 2:  # 16 rows
        r = {"input": t}
        r.update(ca._engine_axes(t, engine_policy))
        assert "engine_lambda" in r and "engine_axes" in r and "engine_label" in r
        r["label"] = r["engine_label"]  # typed-corpus doctrine: engine is the oracle
        rows.append(r)
    policy = ca.calibrate(rows, alpha=0.2, delta=0.2)
    assert policy["n_calibration"] + policy["n_holdout"] == len(rows)
    assert ca.check_policy(policy) == []
