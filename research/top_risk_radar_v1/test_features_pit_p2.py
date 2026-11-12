"""Synthetic P2 feature tests; no historical prices or performance evaluation."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import math

import pytest

from research.top_risk_radar_v1.features import DailyClose, build_daily_features, FEATURE_SCHEMA_VERSION

UTC = timezone.utc
DECISION = datetime(2026, 11, 12, 0, 5, tzinfo=UTC)


def sample(symbol, rate=0.01):
    start = DECISION.replace(hour=0, minute=0) - timedelta(days=30)
    return [DailyClose(symbol, start + timedelta(days=i),
                       start + timedelta(days=i, minutes=1),
                       start + timedelta(days=i, minutes=2),
                       100 * math.exp(rate * i)) for i in range(31)]


def test_exact_synthetic_returns_vol_drawdown_and_schema():
    f = build_daily_features(sample("XRPUSDT", .01), sample("BTCUSDT", .004), DECISION)
    assert f["schema_version"] == FEATURE_SCHEMA_VERSION
    assert f["xrp_log_return_30d"] == pytest.approx(.3)
    assert f["btc_log_return_7d"] == pytest.approx(.028)
    assert f["relative_log_return_1d"] == pytest.approx(.006)
    assert f["xrp_realized_vol_7d"] == pytest.approx(0, abs=1e-12)
    assert f["xrp_drawdown_30d"] == pytest.approx(0)
    assert f["max_available_at_utc"] == "2026-11-12T00:02:00+00:00"
    assert f == build_daily_features(sample("XRPUSDT", .01), sample("BTCUSDT", .004), DECISION)


def test_future_candle_shift_fails_closed():
    x = sample("XRPUSDT")
    x[-1] = replace(x[-1], event_time=DECISION + timedelta(minutes=1))
    with pytest.raises(ValueError, match="not_yet_available"):
        build_daily_features(x, sample("BTCUSDT"), DECISION)


def test_old_event_late_receipt_fails_closed():
    x = sample("XRPUSDT")
    x[0] = replace(x[0], received_at=DECISION)
    with pytest.raises(ValueError, match="not_yet_available"):
        build_daily_features(x, sample("BTCUSDT"), DECISION)


def test_gap_and_duplicate_fail_closed():
    x = sample("XRPUSDT")
    x[8] = replace(x[8], event_time=x[7].event_time)
    with pytest.raises(ValueError, match="missing_or_duplicate"):
        build_daily_features(x, sample("BTCUSDT"), DECISION)


def test_no_shorter_history_or_implicit_fill():
    with pytest.raises(ValueError, match="insufficient_lookback"):
        build_daily_features(sample("XRPUSDT")[1:], sample("BTCUSDT"), DECISION)


def test_naive_timestamp_and_invalid_close_rejected():
    x = sample("XRPUSDT")
    x[0] = replace(x[0], published_at=x[0].published_at.replace(tzinfo=None))
    with pytest.raises(ValueError, match="invalid_source_or_timezone"):
        build_daily_features(x, sample("BTCUSDT"), DECISION)
    x = sample("XRPUSDT")
    x[0] = replace(x[0], close=0)
    with pytest.raises(ValueError, match="invalid_close"):
        build_daily_features(x, sample("BTCUSDT"), DECISION)


def test_same_features_for_both_target_horizons():
    # Features do not accept target or horizon: label maturity is a separate concern.
    a = build_daily_features(sample("XRPUSDT"), sample("BTCUSDT"), DECISION)
    assert "horizon" not in a and "label" not in a
