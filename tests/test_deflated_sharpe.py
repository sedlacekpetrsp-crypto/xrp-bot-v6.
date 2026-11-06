import math
import random

import pytest

from tools.research.deflated_sharpe import (annual_to_period, deflated_sharpe, dsr_from_returns,
                                            expected_max_sharpe, moments, probabilistic_sharpe,
                                            var_from_trial_sharpes)


def test_paper_numeric_example():
    # Bailey & López de Prado (2014), číselný příklad: SR 2,5 p.a., T=1250 dní, N=100,
    # V[SR]=0,5 p.a., skew −3, kurtosis 10 ⇒ DSR ≈ 0,9004
    sr = annual_to_period(2.5, 250)
    var = 0.5 / 250
    assert deflated_sharpe(sr, 1250, 100, var, skew=-3, kurt=10) == pytest.approx(0.9004, abs=2e-3)


def test_single_trial_is_psr_vs_zero():
    assert expected_max_sharpe(1, 0.01) == 0.0
    assert deflated_sharpe(0.05, 500, 1, 0.01) == pytest.approx(probabilistic_sharpe(0.05, 0.0, 500))


def test_normal_psr_closed_form():
    sr, t = 0.05, 400
    expected = 0.5 * (1 + math.erf(sr * math.sqrt(t - 1) / math.sqrt(1 + sr * sr / 2) / math.sqrt(2)))
    assert probabilistic_sharpe(sr, 0.0, t) == pytest.approx(expected, rel=1e-9)


def test_dsr_decreases_with_trials_and_variance():
    vals = [deflated_sharpe(0.08, 730, n, 0.001) for n in (1, 10, 100, 1000)]
    assert all(a > b for a, b in zip(vals, vals[1:]))
    assert deflated_sharpe(0.08, 730, 50, 0.0001) > deflated_sharpe(0.08, 730, 50, 0.004)


def test_negative_skew_and_fat_tails_lower_psr():
    base = probabilistic_sharpe(0.1, 0.0, 730)
    assert probabilistic_sharpe(0.1, 0.0, 730, skew=-2, kurt=9) < base


def test_moments_and_from_returns():
    rnd = random.Random(7)
    r = [rnd.gauss(0.001, 0.02) for _ in range(5000)]
    sr, skew, kurt, t = moments(r)
    assert t == 5000 and abs(skew) < 0.15 and abs(kurt - 3) < 0.3
    out = dsr_from_returns(r, 20, 0.0005)
    assert 0.0 <= out["dsr"] <= out["psr_vs_0"] <= 1.0


def test_var_from_trials_and_errors():
    assert var_from_trial_sharpes([0.0, 0.2]) == pytest.approx(0.02)
    with pytest.raises(ValueError):
        moments([1.0, 1.0, 1.0])
    with pytest.raises(ValueError):
        expected_max_sharpe(0, 0.1)
