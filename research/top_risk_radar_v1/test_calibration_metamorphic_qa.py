"""Synthetic metamorphic QA for calibration diagnostics; no market data or OOS runs."""
import math

import pytest

from research.top_risk_radar_v1.calibration import calibration_metrics


@pytest.mark.parametrize("bins", [2, 3, 10, 100])
def test_reliability_bins_partition_all_rows_and_preserve_event_count(bins):
    rows = [(0.0, False), (0.1, True), (0.5, False), (0.999, True), (1.0, True)]
    result = calibration_metrics(rows, bins=bins)
    assert result["n"] == len(rows)
    assert sum(bucket["n"] for bucket in result["bins"]) == len(rows)
    assert sum(bucket["n"] * bucket["observed_rate"]
               for bucket in result["bins"] if bucket["n"]) == 3
    assert all(bucket["mean_prediction"] is None and bucket["observed_rate"] is None
               for bucket in result["bins"] if not bucket["n"])


def test_log_loss_extreme_probabilities_stays_finite_without_mutating_brier():
    rows = [(0.0, True), (1.0, False)]
    result = calibration_metrics(rows)
    assert result["brier"] == 1.0
    assert math.isfinite(result["log_loss"])
    assert result["log_loss"] > 30


def test_input_rows_are_not_modified_and_result_does_not_depend_on_order():
    rows = [(0.2, False), (0.8, True), (0.5, True)]
    snapshot = rows.copy()
    forward = calibration_metrics(rows, bins=5)
    backward = calibration_metrics(list(reversed(rows)), bins=5)
    assert rows == snapshot
    assert forward["event_rate"] == backward["event_rate"]
    assert forward["brier"] == pytest.approx(backward["brier"])
    assert forward["log_loss"] == pytest.approx(backward["log_loss"])


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -0.001, 1.001, "0.3", None, True])
def test_invalid_probability_anywhere_fails_closed(bad):
    with pytest.raises(ValueError):
        calibration_metrics([(0.5, False), (bad, True)])


@pytest.mark.parametrize("bad", [None, 0, 1, "true", 0.0])
def test_immature_or_non_boolean_label_anywhere_fails_closed(bad):
    with pytest.raises(TypeError):
        calibration_metrics([(0.5, True), (0.2, bad)])
