# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Exact binomial selective-risk bounds on a fixed threshold grid.

Independently implemented from the Learn then Test principle of simultaneous
testing (Angelopoulos et al., https://arxiv.org/abs/2110.01052). This module is
not full conformal risk control or SCoRE. Conditional iid Bernoulli errors are
required. Bonferroni covers a finite grid fixed before calibration labels.
No risk statement survives arbitrary deployment shift or dependent samples.
"""
from __future__ import annotations
import math

ASSUMPTIONS = frozenset({'iid_units', 'held_out_from_training_and_tuning',
                         'predictor_and_scores_frozen', 'grid_fixed_before_labels',
                         'same_target_population'})


def _probability(value, name, *, strictly_positive=False):
    if (type(value) not in (int, float) or not math.isfinite(value)
            or not (0 < value < 1 if strictly_positive else 0 <= value <= 1)):
        raise ValueError('Invalid probability: ' + name)
    return float(value)


def binomial_cdf(errors: int, n: int, p: float) -> float:
    """P[Binomial(n,p) <= errors], evaluated by log-sum-exp."""
    if type(errors) is not int or type(n) is not int or n < 1 or not 0 <= errors <= n:
        raise ValueError('Invalid binomial counts')
    p = _probability(p, 'p')
    if errors == n or p == 0: return 1.0
    if p == 1: return 0.0
    logs = [math.lgamma(n + 1) - math.lgamma(j + 1) - math.lgamma(n - j + 1)
            + j * math.log(p) + (n - j) * math.log1p(-p) for j in range(errors + 1)]
    peak = max(logs)
    return min(1.0, math.exp(peak) * math.fsum(math.exp(x - peak) for x in logs))


def risk_upper_bound(errors: int, accepted: int, alpha: float = 0.05) -> float:
    """One-sided Clopper-Pearson upper bound, confidence 1-alpha.

    Zero observations have no bound. A zero observed error rate never proves
    population risk zero: U(0,n)=1-alpha**(1/n) for any finite positive n.
    """
    if (type(errors) is not int or type(accepted) is not int or accepted < 1
            or accepted > 100000 or not 0 <= errors <= accepted):
        raise ValueError('Positive accepted count and valid errors required (maximum 100000)')
    alpha = _probability(alpha, 'alpha', strictly_positive=True)
    if errors == accepted: return 1.0
    if errors == 0: return -math.expm1(math.log(alpha) / accepted)
    # Large allowed alpha values can put the upper quantile below k/n.
    low, high = 0.0, 1.0
    for _ in range(60):
        midpoint = (low + high) / 2
        if binomial_cdf(errors, accepted, midpoint) > alpha: low = midpoint
        else: high = midpoint
    return min(1.0, math.nextafter(high, 1.0))


def select_threshold(observations: list[dict], *, thresholds: list[float],
                     max_risk: float, delta: float, assumptions: dict) -> dict:
    """Select maximum empirical coverage among simultaneously bounded risks.

    Each observation is one preselected independent unit with a score frozen
    before calibration labels and an externally measured binary error.
    Declarations and unique ids are sanity checks, not independence proofs.
    """
    max_risk = _probability(max_risk, 'max_risk')
    delta = _probability(delta, 'delta', strictly_positive=True)
    if not thresholds or len(thresholds) > 100:
        raise ValueError('A fixed grid of 1..100 thresholds is required')
    grid = [_probability(t, 'threshold') for t in thresholds]
    if len(set(grid)) != len(grid): raise ValueError('Duplicate grid thresholds')
    if not isinstance(assumptions, dict) or set(assumptions) != ASSUMPTIONS:
        raise ValueError('Declare every statistical assumption explicitly')
    if any(type(v) is not bool for v in assumptions.values()):
        raise ValueError('Assumptions require actual booleans')
    if len(observations) > 100000: raise ValueError('Too many calibration units')
    units, families = set(), set()
    for obs in observations:
        if not isinstance(obs, dict) or set(obs) != {'unit_id', 'family_id', 'score', 'error'}:
            raise ValueError('Invalid calibration observation schema')
        for key, seen in [('unit_id', units), ('family_id', families)]:
            if not isinstance(obs[key], str) or not obs[key] or obs[key] in seen:
                raise ValueError('Missing or repeated independent ' + key)
            seen.add(obs[key])
        _probability(obs['score'], 'score')
        if type(obs['error']) is not bool: raise ValueError('Error outcome must be boolean')
    base = {'schema': 'szl.selective-risk/v1', 'calibration_units': len(observations),
            'risk_target': max_risk, 'familywise_error_level': delta,
            'grid': grid, 'per_threshold_alpha': delta / len(grid),
            'assumptions': assumptions, 'release_authorization': 'NONE',
            'limitations': ['Assumptions are caller declarations, not authenticated proofs.',
                            'Bounds concern risk conditional on acceptance for this frozen selector and population.',
                            'Empirical coverage is descriptive, not a lower bound on future coverage.',
                            'No guarantee under arbitrary distribution shift or reused calibration labels.',
                            'This optional risk target does not replace any sealed promotion threshold.']}
    if not observations or not all(assumptions.values()):
        return {**base, 'status': 'UNAVAILABLE', 'selected_threshold': None,
                'reason': 'Empty calibration or statistical assumptions not established', 'candidates': []}
    candidates = []
    for threshold in grid:
        selected = [obs for obs in observations if obs['score'] >= threshold]
        errors = sum(obs['error'] for obs in selected)
        bound = risk_upper_bound(errors, len(selected), delta / len(grid)) if selected else None
        candidates.append({'threshold': threshold, 'accepted': len(selected), 'errors': errors,
                           'empirical_coverage': len(selected) / len(observations),
                           'empirical_risk': errors / len(selected) if selected else None,
                           'risk_upper_bound': bound,
                           'risk_condition_met': bound is not None and bound <= max_risk})
    eligible = [item for item in candidates if item['risk_condition_met']]
    chosen = min(eligible, key=lambda c: (-c['accepted'], c['threshold'])) if eligible else None
    return {**base, 'status': 'CONDITIONAL_BOUND_AVAILABLE' if chosen else 'NO_THRESHOLD_QUALIFIES',
            'selected_threshold': chosen['threshold'] if chosen else None,
            'selected': chosen, 'candidates': candidates}
