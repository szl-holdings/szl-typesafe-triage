import math
import pytest
from szl_triage.selective_risk import ASSUMPTIONS, binomial_cdf, risk_upper_bound, select_threshold

ASSUME = dict.fromkeys(ASSUMPTIONS, True)


def obs(n=100, error=False, score=0.9):
    return [{'unit_id': str(i), 'family_id': 'family-' + str(i), 'score': score, 'error': error}
            for i in range(n)]


def select(rows, grid=None, assumptions=None, risk=0.05):
    return select_threshold(rows, thresholds=grid or [0.5, 0.8], max_risk=risk,
                            delta=0.05, assumptions=ASSUME if assumptions is None else assumptions)


def test_zero_error_bound_is_analytic_and_nonzero():
    assert risk_upper_bound(0, 12) == pytest.approx(1 - 0.05 ** (1 / 12))
    assert risk_upper_bound(0, 12) > 0.22
    assert risk_upper_bound(0, 100) > 0


def test_nonzero_error_bound_matches_reference_beta_quantile():
    # scipy.stats.beta.ppf(0.95, 2, 9), an independent published-distribution reference.
    assert risk_upper_bound(1, 10) == pytest.approx(0.3941633024365047, abs=1e-12)
    upper = risk_upper_bound(3, 20)
    assert binomial_cdf(3, 20, upper) == pytest.approx(0.05, abs=1e-12)


def test_large_alpha_quantile_can_be_below_the_empirical_error_rate():
    # scipy.stats.beta.ppf(0.05, 2, 9), independent of the implemented CDF inversion.
    upper = risk_upper_bound(1, 10, alpha=0.95)
    assert upper == pytest.approx(0.0367714378874651, abs=1e-12)
    assert upper < 1 / 10
    assert binomial_cdf(1, 10, upper) == pytest.approx(0.95, abs=1e-12)


def test_all_errors_have_upper_bound_one():
    assert risk_upper_bound(12, 12) == 1


def test_small_perfect_test_cannot_certify_low_risk():
    result = select(obs(12))
    assert result['status'] == 'NO_THRESHOLD_QUALIFIES'
    assert result['selected_threshold'] is None


def test_multiplicity_makes_bounds_more_conservative():
    single = select(obs(100), [0.5])['selected']['risk_upper_bound']
    multiple = select(obs(100), [0.5, 0.8])['selected']['risk_upper_bound']
    assert multiple > single


def test_zero_coverage_is_not_a_zero_risk_certificate():
    result = select(obs(score=0.1))
    assert result['status'] == 'NO_THRESHOLD_QUALIFIES'
    assert all(c['risk_upper_bound'] is None for c in result['candidates'])


def test_failure_to_declare_independence_is_unavailable():
    assumptions = dict(ASSUME, iid_units=False)
    assert select(obs(), assumptions=assumptions)['status'] == 'UNAVAILABLE'


def test_zero_risk_cannot_be_certified_from_finite_perfect_data():
    assert select(obs(1000), risk=0)['status'] == 'NO_THRESHOLD_QUALIFIES'


@pytest.mark.parametrize('field', ['unit_id', 'family_id'])
def test_duplicate_cluster_or_identity_cannot_inflate_n(field):
    rows = obs(20)
    rows[-1][field] = rows[0][field]
    with pytest.raises(ValueError, match='repeated independent'):
        select(rows)


@pytest.mark.parametrize('value', [True, float('nan'), float('inf'), -1, 2])
def test_invalid_score_is_never_a_certificate(value):
    rows = obs(20); rows[0]['score'] = value
    with pytest.raises(ValueError): select(rows)


def test_risk_monotonic_in_errors_and_sample_size():
    assert risk_upper_bound(0, 100) < risk_upper_bound(0, 20)
    assert risk_upper_bound(1, 100) < risk_upper_bound(10, 100)


def test_empty_calibration_is_unavailable():
    assert select([])['status'] == 'UNAVAILABLE'


def test_confidence_grid_must_be_fixed_and_unique():
    with pytest.raises(ValueError, match='Duplicate'): select(obs(), [0.5, 0.5])
    assert select(obs(), assumptions=dict(ASSUME, grid_fixed_before_labels=False))['status'] == 'UNAVAILABLE'
