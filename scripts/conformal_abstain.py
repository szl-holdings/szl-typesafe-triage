#!/usr/bin/env python3
# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Conformal abstention for the szl-lambda-gate (split conformal calibration).

The fixed policy threshold answers "what did we pick". The conformal threshold
answers "what does a calibration corpus license": a distribution-free,
finite-sample abstention coverage bound instead of a hand-tuned margin.

Guarantee (Vovk; Lei et al.): if calibration and deployment scores are
exchangeable, then P(score_new <= q_hat) >= 1 - alpha holds EXACTLY, for any
underlying distribution - no smoothness, independence, or model-form
assumptions. The bound is conditional: corpus drift breaks exchangeability
and voids the guarantee until recalibration. This module refuses to issue a
policy without recording that condition (honesty rule, doctrine v11).

Composition with the engine gate (fail-closed):
    lambda >= tau_conformal AND every axis inside its conformal band
        -> MEASURED_GUARANTEED (abstention coverage >= 1 - alpha)
    anything else
        -> CONFORMAL_ABSTAIN; the engine's REVIEW path still owns the input.

The conformal coverage bound is a DIFFERENT quantity from the trust ceiling:
it bounds abstention coverage, not model competence. No competence claim is
made here.

Usage:
    python scripts/conformal_abstain.py --calibrate \
        --data out/engine_coverage_set.jsonl --alpha 0.1 --delta 0.05 \
        --out out/conformal_policy.json --receipt out/conformal_receipt.json
    python scripts/conformal_abstain.py --check --policy out/conformal_policy.json
    python scripts/conformal_abstain.py --apply --policy out/conformal_policy.json \
        --text "charged twice on invoice INV-2041, want a refund"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

POLICY_SCHEMA = "szl.conformal-policy/v1"
RECEIPT_SCHEMA = "szl.conformal-receipt/v1"
HONESTY_CONDITION = (
    "Guarantee holds only under exchangeability of calibration and deployment "
    "scores. Corpus drift voids it; recalibrate on a current corpus before "
    "relying on the bound."
)


class ConformalError(ValueError):
    """Fail-closed: calibration or verification refused to proceed."""


def conformal_quantile(scores: list[float], alpha: float) -> float:
    """The ceil((n+1)*(1-alpha))-th smallest score; None-equivalent when data is insufficient.

    With k = ceil((n+1)*(1-alpha)) > n there are not enough calibration points
    to license level 1-alpha; callers must fail closed instead of extrapolating.
    """
    n = len(scores)
    k = math.ceil((n + 1) * (1.0 - alpha))
    if k > n or k < 1:
        raise ConformalError(
            f"insufficient calibration data: n={n} cannot license alpha={alpha} "
            f"(need k={k} <= n). Add calibration rows or raise alpha."
        )
    ordered = sorted(scores)
    return ordered[k - 1]


def hoeffding_lower_bound(empirical: float, n: int, delta: float) -> float:
    """Finite-sample lower bound: cov >= empirical - sqrt(ln(1/delta)/(2n))."""
    if n <= 0:
        raise ConformalError("Hoeffding bound undefined for n<=0")
    return empirical - math.sqrt(math.log(1.0 / delta) / (2.0 * n))


def load_rows(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _engine_axes(text: str, policy) -> dict[str, float]:
    from szl_triage.pipeline import decide

    d = decide(text, policy)
    axes = {k: float(v) for k, v in dict(d.axes).items()}
    return {"engine_axes": axes, "engine_lambda": float(d.lambda_value), "engine_label": str(d.label).upper()}


def calibrate(rows: list[dict], alpha: float, delta: float, holdout_frac: float = 0.3,
              engine_policy=None) -> dict:
    """Split-conformal calibration over correctly-handled corpus rows.

    Nonconformity score s = 1 - lambda (higher = more unlike calibrated
    correct rows). Per-axis bands use Bonferroni level 1 - alpha/K.
    """
    if not 0.0 < alpha < 1.0 or not 0.0 < delta < 1.0:
        raise ConformalError("alpha and delta must be in (0,1)")
    rows = [r for r in rows if r.get("engine_lambda") is not None]
    correct = [r for r in rows if str(r.get("engine_label", "")).upper() == str(r.get("label", "")).upper()]
    if len(correct) < 10:
        raise ConformalError(f"only {len(correct)} correctly-handled rows; >= 10 required")

    # Deterministic split: sorted by input hash so the split is reproducible.
    correct.sort(key=lambda r: hashlib.sha256(str(r.get("input", "")).encode("utf-8")).hexdigest())
    n_ho = max(1, int(len(correct) * holdout_frac))
    holdout, calib = correct[:n_ho], correct[n_ho:]

    scores = [1.0 - float(r["engine_lambda"]) for r in calib]
    q_hat = conformal_quantile(scores, alpha)
    tau_conformal = round(1.0 - q_hat, 6)

    # Per-axis bands (Bonferroni: level 1 - alpha/K across K axes).
    axis_names: list[str] = []
    for r in calib:
        ax = r.get("engine_axes")
        if isinstance(ax, dict) and ax:
            axis_names = sorted(ax.keys())
            break
    bands: dict[str, dict] = {}
    unbanded: dict[str, str] = {}
    if axis_names and engine_policy is not None:
        per_axis_alpha = alpha / len(axis_names)
        for name in axis_names:
            vals = [float(r["engine_axes"][name]) for r in calib
                    if isinstance(r.get("engine_axes"), dict) and name in r["engine_axes"]]
            k_needed = math.ceil((len(vals) + 1) * (1.0 - per_axis_alpha))
            if len(vals) >= 10 and k_needed <= len(vals):
                med = sorted(vals)[len(vals) // 2]
                disp = [abs(v - med) for v in vals]
                q_ax = conformal_quantile(disp, per_axis_alpha)
                bands[name] = {"center": round(med, 6), "half_width": round(q_ax, 6),
                               "level": round(1.0 - per_axis_alpha, 6)}
            else:
                # Fail-closed honesty: record WHY an axis carries no band.
                unbanded[name] = (f"n={len(vals)} cannot license per-axis "
                                  f"alpha={per_axis_alpha} (need k={k_needed}); "
                                  f"add calibration rows or raise alpha")

    ho_scores = [1.0 - float(r["engine_lambda"]) for r in holdout]
    empirical = sum(1 for s in ho_scores if s <= q_hat) / len(ho_scores)
    bound = hoeffding_lower_bound(empirical, len(ho_scores), delta)

    return {
        "schema": POLICY_SCHEMA,
        "alpha": alpha,
        "delta": delta,
        "n_calibration": len(calib),
        "n_holdout": len(holdout),
        "tau_conformal": tau_conformal,
        "per_axis_bands": bands,
        "axes_unbanded": unbanded,
        "empirical_coverage": round(empirical, 6),
        "hoeffding_lower_bound": round(bound, 6),
        "coverage_claim": (
            f"Under exchangeability, abstention coverage >= {round(1.0 - alpha, 4)} "
            f"exactly; empirical holdout coverage {round(empirical, 4)} with "
            f"finite-sample lower bound {round(bound, 4)} at delta={delta}."
        ),
        "honesty_condition": HONESTY_CONDITION,
        "trust_ceiling_relation": "bounds abstention coverage only; makes no competence claim",
    }


def check_policy(policy: dict) -> list[str]:
    """Fail-closed verification; returns the list of verified invariants."""
    problems: list[str] = []
    if policy.get("schema") != POLICY_SCHEMA:
        problems.append(f"schema mismatch: {policy.get('schema')!r}")
    for key in ("alpha", "delta", "tau_conformal", "empirical_coverage", "hoeffding_lower_bound"):
        if policy.get(key) is None:
            problems.append(f"missing field: {key}")
    if problems:
        return problems
    alpha, delta = float(policy["alpha"]), float(policy["delta"])
    if not 0.0 < alpha < 1.0 or not 0.0 < delta < 1.0:
        problems.append("alpha/delta out of (0,1)")
    tau = float(policy["tau_conformal"])
    if not 0.0 <= tau <= 1.0:
        problems.append(f"tau_conformal out of [0,1]: {tau}")
    recomputed = hoeffding_lower_bound(float(policy["empirical_coverage"]),
                                      int(policy["n_holdout"]), delta)
    if abs(recomputed - float(policy["hoeffding_lower_bound"])) > 1e-6:
        problems.append(f"hoeffding bound mismatch: recorded {policy['hoeffding_lower_bound']}, recomputed {recomputed:.6f}")
    if policy.get("honesty_condition") != HONESTY_CONDITION:
        problems.append("honesty condition text missing or altered")
    return problems


def apply_policy(policy: dict, text: str, engine_policy) -> dict:
    """Combine the engine decision with the conformal threshold (fail-closed)."""
    from szl_triage.pipeline import decide

    d = decide(text, engine_policy)
    lam = float(d.lambda_value)
    tau = float(policy["tau_conformal"])
    in_bands = True
    band_detail: dict[str, bool] = {}
    axes = {k: float(v) for k, v in dict(d.axes).items()}
    for name, band in (policy.get("per_axis_bands") or {}).items():
        v = axes.get(name)
        ok = v is not None and (band["center"] - band["half_width"]) <= v <= (band["center"] + band["half_width"])
        band_detail[name] = ok
        in_bands = in_bands and ok
    verdict = "MEASURED_GUARANTEED" if (lam >= tau and in_bands) else "CONFORMAL_ABSTAIN"
    return {
        "engine_label": str(d.label).upper(),
        "lambda": round(lam, 6),
        "tau_conformal": tau,
        "axes": axes,
        "per_axis_in_band": band_detail,
        "conformal_verdict": verdict,
        "coverage_claim": policy["coverage_claim"],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--data", type=Path, default=ROOT / "out" / "engine_coverage_set.jsonl")
    ap.add_argument("--policy", type=Path, default=ROOT / "out" / "conformal_policy.json")
    ap.add_argument("--receipt", type=Path, default=ROOT / "out" / "conformal_receipt.json")
    ap.add_argument("--out", type=Path, default=ROOT / "out" / "conformal_policy.json")
    ap.add_argument("--text")
    ap.add_argument("--alpha", type=float, default=0.1)
    ap.add_argument("--delta", type=float, default=0.05)
    ap.add_argument("--recompute-axes", action="store_true",
                    help="run the engine over calibration inputs to attach per-axis scores")
    args = ap.parse_args()

    if not (args.calibrate or args.check or args.apply):
        ap.error("choose --calibrate, --check, or --apply")

    if args.calibrate:
        from szl_triage import load_policy

        engine_policy = load_policy(str(ROOT / "policies" / "triage_policy.v3.json"))
        rows = load_rows(args.data)
        if args.recompute_axes:
            for r in rows:
                if r.get("input") and not r.get("engine_axes"):
                    r.update(_engine_axes(str(r["input"]), engine_policy))
        policy = calibrate(rows, args.alpha, args.delta, engine_policy=engine_policy if args.recompute_axes else None)
        problems = check_policy(policy)
        if problems:
            print(json.dumps({"refused": problems}, indent=2))
            return 2
        args.out.write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")
        receipt = {
            "schema": RECEIPT_SCHEMA,
            "calibration_source": str(args.data),
            "calibration_source_sha256": hashlib.sha256(args.data.read_bytes()).hexdigest(),
            "n_calibration": policy["n_calibration"],
            "n_holdout": policy["n_holdout"],
            "alpha": policy["alpha"],
            "tau_conformal": policy["tau_conformal"],
            "empirical_coverage": policy["empirical_coverage"],
            "hoeffding_lower_bound": policy["hoeffding_lower_bound"],
            "coverage_claim": policy["coverage_claim"],
            "honesty_condition": HONESTY_CONDITION,
        }
        args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "CALIBRATED", "policy": str(args.out), "receipt": str(args.receipt),
                          "tau_conformal": policy["tau_conformal"],
                          "empirical_coverage": policy["empirical_coverage"],
                          "hoeffding_lower_bound": policy["hoeffding_lower_bound"]}, indent=2))
        return 0

    if args.check:
        policy = json.loads(args.policy.read_text(encoding="utf-8"))
        problems = check_policy(policy)
        if problems:
            print(json.dumps({"status": "REFUSED", "problems": problems}, indent=2))
            return 2
        print(json.dumps({"status": "VERIFIED",
                          "invariants": ["schema", "alpha/delta ranges", "tau in [0,1]",
                                         "hoeffding bound recomputation", "honesty condition present"]}, indent=2))
        return 0

    if args.apply:
        if not args.text:
            ap.error("--apply requires --text")
        from szl_triage import load_policy

        engine_policy = load_policy(str(ROOT / "policies" / "triage_policy.v3.json"))
        policy = json.loads(args.policy.read_text(encoding="utf-8"))
        problems = check_policy(policy)
        if problems:
            print(json.dumps({"refused": problems}, indent=2))
            return 2
        print(json.dumps(apply_policy(policy, args.text, engine_policy), indent=2))
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
