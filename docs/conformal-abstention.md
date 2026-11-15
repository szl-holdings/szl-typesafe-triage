# Conformal abstention over the Lambda gate

## What problem this solves

The engine's fixed threshold (policies/triage_policy.v3.json, lambda_threshold
= 0.65) answers "what did we pick". It says nothing about what a calibration
corpus licenses. Conformal abstention adds the missing, distribution-free
layer: a threshold tau_conformal with an EXACT finite-sample guarantee, plus
tamper-evident receipts.

## The math

Split conformal prediction (Vovk; Lei et al.):

1. Take a calibration corpus of correctly-handled rows; split it
   deterministically (sha256-ordered, 30% holdout).
2. Score each calibration row by nonconformity s = 1 - lambda (higher = less
   like a confident-correct row).
3. tau_conformal = 1 - q_hat where q_hat is the EXACT order statistic
   scores[(ceil((n+1)(1-alpha)))] (the ceil((n+1)(1-alpha))-th smallest).
   If that index exceeds n, calibration refuses fail-closed: the data cannot
   license the requested alpha.
4. Guarantee: if calibration and deployment scores are exchangeable,
   P(s_new <= q_hat) >= 1 - alpha EXACTLY, for any underlying distribution.
   No smoothness, independence, or model-form assumptions.
5. Finite-sample audit: empirical holdout coverage gets a Hoeffding lower
   bound emp - sqrt(ln(1/delta)/2n) at confidence delta; check_policy()
   recomputes it, so a tampered receipt fails verification.

Per-axis bands use Bonferroni correction (level 1 - alpha/K per axis). An axis
with too few rows to license its Bonferroni level is recorded under
axes_unbanded with the reason - never silently dropped.

## Composition with the engine (fail-closed)

    lambda >= tau_conformal AND every banded axis inside its band
        -> MEASURED_GUARANTEED (abstention coverage >= 1 - alpha)
    anything else
        -> CONFORMAL_ABSTAIN; the engine REVIEW path still owns the input.

The conformal layer is STRICTER than the engine gate, never looser.

## Measured result (2026-11-15, corpus sha 505770b6...)

Calibration set: scripts/build_conformal_calibration.py over the typed triage
corpus (state=MEASURED rows only, gold = template bucket; the typed corpus is
engine-as-oracle by design - see its header doctrine).

Population finding, reported honestly: of 137 typed-confident rows, the
current engine (policy v3.1.0) reproduces the typed intent on only 16
(12 BILLING, 4 BUG); it routes the other 121 to REVIEW and confidently
mislabels ZERO. The engine has hardened since the v0.5.0 corpus build; it
refuses rather than errs. The conformal layer is calibrated over the
confident regime that remains.

- alpha = 0.1, delta = 0.05
- n_calibration = 12, n_holdout = 4 (small-sample caveat: the Hoeffding lower
  bound 0.388 is correspondingly wide; the exact conformal bound is
  distribution-free and does not depend on n being large)
- tau_conformal = 0.8503 (vs engine hard threshold 0.65)
- empirical holdout coverage = 1.0
- axes_unbanded: all 4 axes (n=12 cannot license Bonferroni alpha=0.025,
  k=13 > 12) - recorded, not hidden

Remediation to unlock per-axis bands: grow the confident-correct population
(regenerate the typed corpus under the current policy, or ratify more rows),
then re-run calibrate.

## Honesty rules (binding)

- The guarantee is conditional on exchangeability of calibration and
  deployment scores. Corpus drift voids it until recalibration. This text is
  embedded in every policy and receipt and check_policy refuses a policy
  whose honesty clause is altered.
- Coverage is NOT competence: the bound is about abstention coverage, not
  about the trust ceiling. No competence claim is made.
- The typed corpus is engine-as-oracle: tau_conformal licenses
  lambda-typicality under the typed distribution, not real-traffic
  correctness.

## Usage

    python scripts/build_conformal_calibration.py
    python scripts/conformal_abstain.py --calibrate \
        --data out/conformal_calibration_set.jsonl --alpha 0.1 --delta 0.05 \
        --recompute-axes --out out/conformal_policy.json \
        --receipt out/conformal_receipt.json
    python scripts/conformal_abstain.py --check --policy out/conformal_policy.json
    python scripts/conformal_abstain.py --apply --policy out/conformal_policy.json \
        --text "charged twice on invoice INV-2041, want a refund"

Artifacts: out/conformal_policy.json (szl.conformal-policy/v1),
out/conformal_receipt.json (szl.conformal-receipt/v1),
out/conformal_calibration_set.jsonl (szl.conformal-calibration-set/v1).

References: Vovk et al., Algorithmic Learning in a Randomized World (2005);
Lei et al., Distribution-Free Prediction Bands (JASA 2018);
arXiv:2604.27914 (conformal abstention for LLM decision systems).
