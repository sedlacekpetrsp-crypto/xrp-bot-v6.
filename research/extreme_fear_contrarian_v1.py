"""Frozen XRP extreme-fear contrarian simulator (offline only)."""
from dataclasses import dataclass
from math import isfinite

from research.realized_value_discount_v1 import DAY, atr, backtest as _backtest, signal_at as _signal_at


@dataclass(frozen=True)
class Config:
    max_fear: int = 20
    atr_n: int = 14
    stop_atr: float = 2.0
    reward_r: float = 3.0
    max_hold: int = 10
    risk_fraction: float = 0.005
    notional_cap: float = 0.20
    fee: float = 0.00095
    slippage: float = 0.00020

    @property
    def discount(self):
        return self.max_fear


def validate(rows):
    times = [item["timestamp"] for item in rows]
    if any(timestamp % DAY for timestamp in times) or any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("timestamp")
    for item in rows:
        values = [float(item[key]) for key in ("open", "high", "low", "close")]
        fear = float(item["fear"])
        if not all(isfinite(value) for value in values + [fear]):
            raise ValueError("finite")
        o, h, l, c = values
        if not 0 < l <= min(o, c) <= max(o, c) <= h or not 0 <= fear <= 100 or fear != int(fear):
            raise ValueError("values")


def _base_rows(rows):
    return [{**item, "mvrv": item["fear"]} for item in rows]


def signal_at(rows, i, config=Config()):
    """At decision close i, use only the exact prior day's sentiment."""
    return _signal_at(_base_rows(rows), i, config)


def backtest(rows, start, end, config=Config(), initial=10_000.0):
    validate(rows)
    trades, curve = _backtest(_base_rows(rows), start, end, config, initial)
    for trade in trades:
        trade["signal_fear"] = trade.pop("signal_mvrv")
    return trades, curve
