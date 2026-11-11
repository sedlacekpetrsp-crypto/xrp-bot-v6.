"""Synthetic calibration metric unit tests, shared by XRP radar targets.

No historical observations, predictions, model training or performance runs.
"""
import math

import pytest

from research.top_risk_radar_v1.calibration_metrics import (
    brier_score, calibration_bins, log_loss,
)


def test_perfect_probabilities_have_zero_error():
    assert brier_score([0.0, 1.0], [0, 1]) == 0.0
    assert log_loss([0.0, 1.0], [0, 1]) == 0.0


def test_wrong_certain_forecast_has_infinite_log_loss():
    assert math.isinf(log_loss([0.0, 1.0], [1, 0]))
    assert brier_score([0.0, 1.0], [1, 0]) == 1.0


def test_half_probability_has_known_scores():
    assert brier_score([0.5, 0.5], [0, 1]) == pytest.approx(0.25)
    assert log_loss([0.5, 0.5], [0, 1]) == pytest.approx(math.log(2))


def test_boundary_one_belongs_to_last_bin():
    rows = calibration_bins([0.0, 0.5, 1.0], [0, 1, 1], bins=2)
    assert rows[0] == {"bin": 0, "count": 1, "mean_prediction": 0.0, "event_rate": 0.0}
    assert rows[1]["count"] == 2
    assert rows[1]["mean_prediction"] == pytest.approx(0.75)
    assert rows[1]["event_rate"] == 1.0


@pytest.mark.parametrize("invalid", [-0.1, 1.1, float("nan"), float("inf"), -float("inf")])
def test_nonprobabilities_fail_closed(invalid):
    with pytest.raises(ValueError):
        brier_score([invalid], [1])


@pytest.mark.parametrize("invalid", [None, "0.5", True])
def test_non_numeric_probabilities_fail_closed(invalid):
    with pytest.raises(TypeError):
        log_loss([invalid], [0])


@pytest.mark.parametrize("invalid", [None, True, 2, -1, 0.5, "1"])
def test_nonbinary_or_censored_outcomes_fail_closed(invalid):
    with pytest.raises(ValueError):
        calibration_bins([0.5], [invalid])


def test_length_mismatch_and_empty_rejected():
    with pytest.raises(ValueError):
        brier_score([], [])
    with pytest.raises(ValueError):
        log_loss([0.5], [])
    with pytest.raises(ValueError):
        calibration_bins([0.5, 0.6], [1])


@pytest.mark.parametrize("invalid", [0, 1, True, 2.0, -1])
def test_invalid_bin_count_rejected(invalid):
    with pytest.raises(ValueError):
        calibration_bins([0.5], [1], bins=invalid)


def test_no_smoothing_or_clipping_hidden():
    assert log_loss([1.0], [1]) == 0.0
    assert math.isinf(log_loss([1.0], [0]))
