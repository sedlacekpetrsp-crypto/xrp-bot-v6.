"""Synthetic-only calibration aggregation invariants for both XRP PAPER radars.

These tests validate reporting arithmetic, not predictive performance or OOS skill.
"""
import math
import random

import pytest

from research.top_risk_radar_v1.calibration_metrics import calibration_bins, score


@pytest.mark.parametrize("n_bins", [2, 3, 10, 100])
def test_calibration_weighted_aggregates_reconstruct_global_means(n_bins):
    rng = random.Random(20261113)
    probabilities = [0.0, 1.0] + [rng.random() for _ in range(997)]
    outcomes = [0, 1] + [rng.randrange(2) for _ in range(997)]
    result = score(probabilities, outcomes, bins=n_bins)
    rows = result["bins"]
    assert len(rows) == n_bins
    assert sum(row["count"] for row in rows) == len(outcomes)
    observed_rate = math.fsum(row["count"] * row["event_rate"] for row in rows if row["count"]) / len(outcomes)
    predicted_rate = math.fsum(row["count"] * row["mean_prediction"] for row in rows if row["count"]) / len(outcomes)
    assert observed_rate == pytest.approx(result["event_rate"], abs=1e-14)
    assert predicted_rate == pytest.approx(math.fsum(probabilities) / len(probabilities), abs=1e-14)


@pytest.mark.parametrize("n_bins", [2, 10, 100])
def test_replicating_all_rows_does_not_change_calibration_rates(n_bins):
    p = [0.0, 0.1, 0.19, 0.2, 0.49, 0.5, 0.8, 0.99, 1.0]
    y = [0, 1, 0, 1, 0, 1, 0, 1, 1]
    original = score(p, y, bins=n_bins)
    replicated = score(p * 7, y * 7, bins=n_bins)
    assert replicated["n"] == 7 * original["n"]
    assert replicated["brier"] == pytest.approx(original["brier"])
    assert replicated["log_loss"] == pytest.approx(original["log_loss"])
    assert replicated["event_rate"] == pytest.approx(original["event_rate"])
    for a, b in zip(original["bins"], replicated["bins"]):
        assert b["count"] == 7 * a["count"]
        assert b["event_rate"] == pytest.approx(a["event_rate"]) if a["count"] else b["event_rate"] is None
        assert b["mean_prediction"] == pytest.approx(a["mean_prediction"]) if a["count"] else b["mean_prediction"] is None


def test_exact_bin_boundary_allocation_matches_half_open_contract():
    p = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    rows = calibration_bins(p, [0] * len(p), bins=10)
    assert [row["count"] for row in rows] == [1, 1, 1, 1, 1, 1, 1, 1, 1, 2]
