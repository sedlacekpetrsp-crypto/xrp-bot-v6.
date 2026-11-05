"""Frozen Bitcoin-miner-revenue recovery signal with shared daily execution."""
from dataclasses import dataclass, replace
from math import isfinite
from statistics import median

from research.xrp_bank_credit_expansion_v1 import (
    Config as ExecutionConfig,
    DAY,
    backtest as _base_backtest,
    validate_prices,
)


@dataclass(frozen=True)
class SignalConfig:
    median_lookback: int = 90
    trend_window: int = 7
    release_lag: int = 2


def make_signals(observations, config=SignalConfig()):
    times = [row["timestamp"] for row in observations]
    if any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("miner revenue timestamp")
    if any(not isfinite(float(row["value"])) or float(row["value"]) < 0 for row in observations):
        raise ValueError("miner revenue value")

    signals = {}
    first = config.release_lag + config.median_lookback
    for eligible_i in range(first, len(observations)):
        latest_i = eligible_i - config.release_lag
        latest = float(observations[latest_i]["value"])
        history = [float(row["value"]) for row in observations[latest_i - config.median_lookback : latest_i]]
        recent = [float(row["value"]) for row in observations[latest_i - config.trend_window + 1 : latest_i + 1]]
        previous = [float(row["value"]) for row in observations[latest_i - 2 * config.trend_window + 1 : latest_i - config.trend_window + 1]]
        threshold = median(history)
        recent_mean = sum(recent) / len(recent)
        previous_mean = sum(previous) / len(previous)
        if latest > threshold and recent_mean > previous_mean:
            signals[observations[eligible_i]["timestamp"]] = {
                "metric_timestamp": observations[latest_i]["timestamp"],
                "window_start_timestamp": observations[latest_i - config.median_lookback]["timestamp"],
                "prior_median": threshold,
                "latest_miner_revenue": latest,
                "recent7_mean": recent_mean,
                "previous7_mean": previous_mean,
            }
    return signals


def execution_config(multiplier=1):
    base = ExecutionConfig(max_hold=5)
    return replace(base, fee=base.fee * multiplier, slippage=base.slippage * multiplier)


def backtest(rows, start, end, config, initial=10000.0):
    normalized = []
    for original in rows:
        row = dict(original)
        if row.get("macro_signal"):
            row.setdefault("earlier_timestamp", row["metric_timestamp"])
            row.setdefault("earlier_credit", row["previous7_mean"])
            row.setdefault("latest_credit", row["latest_miner_revenue"])
            row.setdefault("credit_growth", (row["recent7_mean"] - row["previous7_mean"]) / (row["previous7_mean"] or 1))
        normalized.append(row)
    trades, curve = _base_backtest(normalized, start, end, config, initial)
    signals = {row["timestamp"]: row for row in normalized if row.get("macro_signal")}
    for trade in trades:
        source = signals[trade["signal_timestamp"]]
        for key in ("window_start_timestamp", "prior_median", "latest_miner_revenue", "recent7_mean", "previous7_mean"):
            trade[key] = source[key]
    return trades, curve
