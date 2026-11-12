"""PIT-only daily-close feature extraction for XRP PAPER radar V1 (P2).

Synthetic/unit use only. A candle is eligible only when its close event and
provider publication/collector receipt all precede the decision timestamp.
No imputation, no external data retrieval, no fitting, no trading.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
from collections.abc import Sequence

FEATURE_SCHEMA_VERSION = "radar-features-daily-v1"
WINDOW_DAYS = 30
UTC = timezone.utc


@dataclass(frozen=True)
class DailyClose:
    symbol: str
    event_time: datetime
    published_at: datetime
    received_at: datetime
    close: float


def _utc(value: datetime) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() == timedelta(0)


def _validated(candles: Sequence[DailyClose], symbol: str, decision_time: datetime) -> list[DailyClose]:
    if not _utc(decision_time):
        raise ValueError("decision_time must be timezone-aware UTC")
    if decision_time.hour != 0 or decision_time.minute != 5 or decision_time.second or decision_time.microsecond:
        raise ValueError("decision_time must be 00:05:00 UTC")
    if len(candles) != WINDOW_DAYS + 1:
        raise ValueError("insufficient_lookback: require exactly 31 daily closes")
    ordered = sorted(candles, key=lambda c: c.event_time)
    for c in ordered:
        if c.symbol != symbol or not all(_utc(t) for t in (c.event_time, c.published_at, c.received_at)):
            raise ValueError("invalid_source_or_timezone")
        if isinstance(c.close, bool) or not isinstance(c.close, (int, float)):
            raise ValueError("invalid_close")
        if not math.isfinite(c.close) or c.close <= 0:
            raise ValueError("invalid_close")
        if c.event_time >= decision_time or max(c.published_at, c.received_at) >= decision_time:
            raise ValueError("not_yet_available")
        if c.event_time.hour or c.event_time.minute or c.event_time.second or c.event_time.microsecond:
            raise ValueError("non_daily_close_boundary")
        if c.published_at < c.event_time or c.received_at < c.event_time:
            raise ValueError("invalid_source_chronology")
    expected_last = decision_time.replace(hour=0, minute=0)
    if ordered[-1].event_time != expected_last:
        raise ValueError("missing_latest_daily_close")
    for prev, cur in zip(ordered, ordered[1:]):
        if cur.event_time - prev.event_time != timedelta(days=1):
            raise ValueError("missing_or_duplicate_daily_close")
    return ordered


def build_daily_features(
    xrp: Sequence[DailyClose], btc: Sequence[DailyClose], decision_time: datetime
) -> dict:
    """Return versioned numeric PIT features from 31 continuous UTC daily closes.

    The candle at 00:00 UTC must have been received/published before 00:05 UTC.
    This deliberately requires complete 30-day history; no forward fill.
    """
    a = _validated(xrp, "XRPUSDT", decision_time)
    b = _validated(btc, "BTCUSDT", decision_time)
    x, z = [c.close for c in a], [c.close for c in b]
    out = {"schema_version": FEATURE_SCHEMA_VERSION, "decision_time_utc": decision_time.isoformat(),
           "max_event_time_utc": max(a[-1].event_time, b[-1].event_time).isoformat(),
           "max_available_at_utc": max(*(max(c.published_at, c.received_at) for c in a + b)).isoformat()}
    for d in (1, 7, 30):
        xr = math.log(x[-1] / x[-1-d])
        br = math.log(z[-1] / z[-1-d])
        out[f"xrp_log_return_{d}d"] = xr
        out[f"btc_log_return_{d}d"] = br
        out[f"relative_log_return_{d}d"] = xr - br
    daily = [math.log(x[i] / x[i-1]) for i in range(1, len(x))]
    for d in (7, 30):
        values = daily[-d:]
        mean = math.fsum(values) / d
        out[f"xrp_realized_vol_{d}d"] = math.sqrt(math.fsum((v - mean) ** 2 for v in values) / d)
    peak = max(x[-31:])
    out["xrp_drawdown_30d"] = x[-1] / peak - 1.0
    return out
