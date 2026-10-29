"""Frozen XRP financial-conditions easing simulator (offline only)."""
from dataclasses import dataclass
from math import isfinite

from research.broad_dollar_downtrend_v1 import DAY, atr, backtest as _backtest, signal_at, validate


@dataclass(frozen=True)
class Config:
    macro_lookback: int = 8
    release_lag: int = 2
    max_level: float = -0.25
    max_change: float = -0.10
    atr_n: int = 14
    stop_atr: float = 2.0
    reward_r: float = 3.0
    max_hold: int = 10
    risk_fraction: float = 0.005
    notional_cap: float = 0.20
    fee: float = 0.00095
    slippage: float = 0.00020


def make_signals(macro, config=Config()):
    """Create one signal per eligible weekly NFCI observation."""
    times = [item["timestamp"] for item in macro]
    if any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("macro timestamp")
    if any(not isfinite(item["value"]) for item in macro):
        raise ValueError("macro value")
    out = {}
    first = config.release_lag + config.macro_lookback
    for eligible in range(first, len(macro)):
        latest = eligible - config.release_lag
        earlier = latest - config.macro_lookback
        level = macro[latest]["value"]
        change = level - macro[earlier]["value"]
        if level <= config.max_level and change <= config.max_change:
            out[macro[eligible]["timestamp"]] = {
                "metric_timestamp": macro[latest]["timestamp"],
                "macro_return": change,
                "macro_level": level,
            }
    return out


def backtest(rows, start, end, config=Config(), initial=10_000.0):
    """Run shared execution mechanics and retain the second frozen NFCI filter."""
    trades, curve = _backtest(rows, start, end, config, initial)
    levels = {item["timestamp"]: item.get("macro_level") for item in rows if item.get("macro_signal")}
    for trade in trades:
        trade["macro_level"] = levels[trade["signal_timestamp"]]
    return trades, curve
