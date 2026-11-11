"""Metamorphic QA for calibration arithmetic; synthetic rows only.

No historical predictions, model fitting, backtesting or performance claims.
"""
import math

import pytest

from research.top_risk_radar_v1.calibration import calibration_metrics


def test_permutation_invariance_of_diagnostics_and_reliability_bins():
    rows = [(0.1, False), (0.3, True), (0.6, False), (0.9, True)]
    forward = calibration_metrics(rows, bins=4)
    backward = calibration_metrics(list(reversed(rows)), bins=4)
    assert forward == backward


def test_complement_symmetry_for_brier_and_log_loss():
    rows = [(0.1, False), (0.2, True), (0.7, False), (0.9, True)]
    complemented = [(1.0 - p, not y) for p, y in rows]
    a = calibration_metrics(rows, bins=5)
    b = calibration_metrics(complemented, bins=5)
    assert a["brier"] == pytest.approx(b["brier"])
    assert a["log_loss"] == pytest.approx(b["log_loss"])
    assert a["event_rate"] + b["event_rate"] == pytest.approx(1.0)


def test_constant_probability_matches_analytic_brier_and_entropy():
    rows = [(0.25, False)] * 3 + [(0.25, True)]
    result = calibration_metrics(rows, bins=4)
    assert result["n"] == 4
    assert result["event_rate"] == pytest.approx(0.25)
    assert result["brier"] == pytest.approx(0.1875)
    assert result["log_loss"] == pytest.approx(-0.75 * math.log(0.75) - 0.25 * math.log(0.25))
    assert sum(b["n"] for b in result["bins"]) == 4
    assert sum(b["n"] for b in result["bins"] if b["observed_rate"] is not None) == 4


def test_perfect_and_inverted_predictions_have_distinct_losses():
    perfect = calibration_metrics([(0.0, False), (1.0, True)], bins=2)
    inverted = calibration_metrics([(1.0, False), (0.0, True)], bins=2)
    assert perfect["brier"] == pytest.approx(0.0)
    assert inverted["brier"] == pytest.approx(1.0)
    assert math.isfinite(inverted["log_loss"])
    assert inverted["log_loss"] > perfect["log_loss"]


def test_reliability_bin_counts_and_rates_reconcile_with_global_rate():
    rows = [(0.0, False), (0.25, True), (0.5, True), (0.75, False), (1.0, True)]
    result = calibration_metrics(rows, bins=4)
    populated = [b for b in result["bins"] if b["n"]]
    assert sum(b["n"] for b in populated) == result["n"]
    weighted_event_rate = sum(b["n"] * b["observed_rate"] for b in populated) / result["n"]
    assert weighted_event_rate == pytest.approx(result["event_rate"])
    assert all(b["lower"] <= b["mean_prediction"] <= b["upper"] for b in populated)
