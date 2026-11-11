"""Synthetic contract tests for pure calibration diagnostics (no predictive fit)."""
import math
import pytest
from research.top_risk_radar_v1.calibration import calibration_metrics


def test_perfect_extreme_predictions_have_zero_brier_and_finite_log_loss():
    result = calibration_metrics([(0.0, False), (1.0, True)], bins=2)
    assert result["n"] == 2
    assert result["event_rate"] == 0.5
    assert result["brier"] == 0.0
    assert math.isfinite(result["log_loss"])
    assert result["log_loss"] >= 0


def test_fixed_bins_include_probability_one_in_last_bin():
    result = calibration_metrics([(0.0, False), (0.5, True), (1.0, True)], bins=2)
    assert [b["n"] for b in result["bins"]] == [1, 2]
    assert result["bins"][1]["mean_prediction"] == 0.75


def test_empty_input_is_insufficient_not_perfect():
    result = calibration_metrics([], bins=4)
    assert result["status"] == "insufficient_data"
    assert result["n"] == 0
    assert result["brier"] is None
    assert result["log_loss"] is None
    assert all(b["observed_rate"] is None for b in result["bins"])


@pytest.mark.parametrize("label", [None, 0, 1, "true", float("nan")])
def test_immature_or_nonboolean_label_rejected(label):
    with pytest.raises(TypeError):
        calibration_metrics([(0.5, label)])


@pytest.mark.parametrize("probability", [float("nan"), float("inf"), -0.01, 1.01, True, None])
def test_invalid_probabilities_rejected(probability):
    with pytest.raises(ValueError):
        calibration_metrics([(probability, True)])


@pytest.mark.parametrize("bins", [0, 1, 101, 2.0, True])
def test_invalid_bins_rejected(bins):
    with pytest.raises(ValueError):
        calibration_metrics([(0.5, True)], bins=bins)
