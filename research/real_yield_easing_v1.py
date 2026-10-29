"""Frozen XRP real-yield easing simulator (offline only)."""
from dataclasses import dataclass
from math import isfinite

from research.broad_dollar_downtrend_v1 import DAY, atr, backtest, signal_at, validate


@dataclass(frozen=True)
class Config:
    macro_lookback: int = 20
    release_lag: int = 2
    max_yield_change: float = -0.25
    atr_n: int = 14
    stop_atr: float = 2.0
    reward_r: float = 3.0
    max_hold: int = 10
    risk_fraction: float = 0.005
    notional_cap: float = 0.20
    fee: float = 0.00095
    slippage: float = 0.00020


def make_signals(macro, config=Config()):
    """Map eligible FRED dates to lagged values without filling calendar gaps."""
    times = [x["timestamp"] for x in macro]
    if any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("macro timestamp")
    if any(not isfinite(x["value"]) for x in macro):
        raise ValueError("macro value")
    out = {}
    first = config.release_lag + config.macro_lookback
    for eligible in range(first, len(macro)):
        latest = eligible - config.release_lag
        earlier = latest - config.macro_lookback
        change = macro[latest]["value"] - macro[earlier]["value"]
        if change <= config.max_yield_change:
            out[macro[eligible]["timestamp"]] = {
                "metric_timestamp": macro[latest]["timestamp"],
                "macro_return": change,
            }
    return out
