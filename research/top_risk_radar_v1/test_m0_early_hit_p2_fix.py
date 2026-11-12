"""P2 bugfix QA (dialog 0301/0302): M0 early-hit positives + bool close.

Synthetic only; no market data, no backtest.
"""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import math

import pytest

from research.top_risk_radar_v1.baselines import HORIZON_HOURS, LabelRow, fit_m0
from research.top_risk_radar_v1.features import DailyClose, build_daily_features

UTC = timezone.utc
TEST = datetime(2026, 11, 12, tzinfo=UTC)
TARGETS = sorted(HORIZON_HOURS)  # growth=720h, downside=336h


def early_hit(decision, hours_after):
    return LabelRow(decision, decision + timedelta(hours=hours_after), 1)


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("hit_hours", [1, 50, "horizon"])
def test_early_positive_accepted_and_counted_when_full_horizon_before_cutoff(target, hit_hours):
    h = HORIZON_HOURS[target]
    hours = h if hit_hours == "horizon" else hit_hours
    d = TEST - timedelta(hours=h + 24)
    out = fit_m0([early_hit(d, hours)], target=target, test_start=TEST)
    assert out["status"] == "fitted_train_only"
    assert out["n_train"] == 1 and out["probability"] == 1.0


@pytest.mark.parametrize("target", TARGETS)
def test_early_positive_excluded_until_full_horizon_elapsed(target):
    # Hit already known before cutoff, but horizon not complete -> excluded
    # (same gate as negatives; prevents early-positive selection bias).
    h = HORIZON_HOURS[target]
    d = TEST - timedelta(hours=h - 24)
    out = fit_m0([early_hit(d, 1)], target=target, test_start=TEST)
    assert out["status"] == "insufficient_train"


@pytest.mark.parametrize("target", TARGETS)
def test_full_horizon_ending_exactly_at_cutoff_excluded(target):
    h = HORIZON_HOURS[target]
    d = TEST - timedelta(hours=h)
    for row in (early_hit(d, 1), LabelRow(d, d + timedelta(hours=h), 0)):
        assert fit_m0([row], target=target, test_start=TEST)["n_train"] == 0


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("offset_hours", [0, -1])
def test_positive_available_at_or_before_decision_rejected(target, offset_hours):
    d = TEST - timedelta(days=60)
    with pytest.raises(ValueError, match="premature_label_availability"):
        fit_m0([LabelRow(d, d + timedelta(hours=offset_hours), 1)], target=target, test_start=TEST)


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("label", [0, None])
def test_negative_or_missing_before_horizon_still_rejected(target, label):
    h = HORIZON_HOURS[target]
    d = TEST - timedelta(days=60)
    with pytest.raises(ValueError, match="premature_label_availability"):
        fit_m0([LabelRow(d, d + timedelta(hours=h - 1), label)], target=target, test_start=TEST)


def test_early_positive_does_not_bias_rate_vs_negatives():
    h = HORIZON_HOURS["downside"]
    old = TEST - timedelta(hours=h + 48)
    recent = TEST - timedelta(hours=h - 48)
    rows = [early_hit(old, 5), LabelRow(old - timedelta(days=1), old - timedelta(days=1) + timedelta(hours=h), 0),
            early_hit(recent, 5)]  # recent positive known, its negatives would not be
    out = fit_m0(rows, target="downside", test_start=TEST)
    assert out["n_train"] == 2 and out["probability"] == 0.5


def _sample(symbol):
    decision = datetime(2026, 11, 12, 0, 5, tzinfo=UTC)
    start = decision.replace(hour=0, minute=0) - timedelta(days=30)
    return decision, [DailyClose(symbol, start + timedelta(days=i), start + timedelta(days=i, minutes=1),
                                 start + timedelta(days=i, minutes=2), 100 * math.exp(0.01 * i))
                      for i in range(31)]


@pytest.mark.parametrize("bad", [True, False, "100", None])
def test_bool_or_non_numeric_close_rejected(bad):
    decision, x = _sample("XRPUSDT")
    _, btc = _sample("BTCUSDT")
    x[3] = replace(x[3], close=bad)
    with pytest.raises(ValueError, match="invalid_close"):
        build_daily_features(x, btc, decision)
