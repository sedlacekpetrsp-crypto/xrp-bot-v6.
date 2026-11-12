"""Synthetic train-only M0 baseline contract; no market outcomes/backtest."""
from datetime import datetime, timedelta, timezone

import pytest

from research.top_risk_radar_v1.baselines import LabelRow, fit_m0

UTC = timezone.utc
TEST = datetime(2026, 11, 12, tzinfo=UTC)


def row(days_ago, label, horizon_hours=336, extra_hours=0):
    t = TEST - timedelta(days=days_ago)
    return LabelRow(t, t + timedelta(hours=horizon_hours + extra_hours), label)


def test_downside_mature_train_only_and_no_test_leakage():
    train = [row(30, 1), row(29, 0), row(28, None), row(2, 1)]
    fitted = fit_m0(train, target="downside", test_start=TEST)
    assert fitted["status"] == "fitted_train_only"
    assert fitted["n_train"] == 2
    assert fitted["probability"] == .5
    # Future/test and immature rows cannot alter fitted prior.
    assert fit_m0(train + [row(-1, 1), row(10, 0)], target="downside", test_start=TEST) == fitted


def test_growth_uses_720h_not_336h():
    train = [row(31, 1, 720), row(20, 0, 720)]
    result = fit_m0(train, target="growth", test_start=TEST)
    assert result["n_train"] == 1
    assert result["probability"] == 1.0


def test_mature_exactly_at_test_start_excluded():
    # Strict PIT: available_at == test_start is not available before decision.
    assert fit_m0([row(31, 1, 720, 24)], target="growth", test_start=TEST)["n_train"] == 0


def test_late_publication_excluded_even_when_event_horizon_elapsed():
    result = fit_m0([row(40, 1, 336, 24 * 50)], target="downside", test_start=TEST)
    assert result["status"] == "insufficient_train"


def test_duplicate_decision_rejected():
    with pytest.raises(ValueError, match="duplicate_decision"):
        fit_m0([row(31, 1), row(31, 0)], target="downside", test_start=TEST)


@pytest.mark.parametrize("label", [False, True, 2, -1, 0.0, "1"])
def test_nonexplicit_binary_label_rejected(label):
    with pytest.raises(ValueError, match="invalid_label"):
        fit_m0([row(31, label)], target="downside", test_start=TEST)


def test_naive_and_early_label_availability_rejected():
    with pytest.raises(ValueError, match="timestamp must be timezone-aware"):
        fit_m0([LabelRow(TEST.replace(tzinfo=None), TEST, 1)], target="downside", test_start=TEST)
    with pytest.raises(ValueError, match="premature_label_availability"):
        fit_m0([LabelRow(TEST - timedelta(days=31), TEST - timedelta(days=30), 1)],
               target="downside", test_start=TEST)


def test_target_isolation():
    with pytest.raises(ValueError, match="unknown_target"):
        fit_m0([], target="other", test_start=TEST)
