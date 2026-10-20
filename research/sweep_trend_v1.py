"""SWEEP_TREND_V1: isolated research backtester; no exchange or order APIs.

Input bars are chronological closed OHLCV dicts. Signal is decided on bar i
close, entry at next bar open. Both-stop-and-target intrabar ambiguity counts
as stop first. This is a hypothesis, not a verified profitable strategy.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    lookback: int = 20
    trend_period: int = 50
    atr_period: int = 14
    min_sweep_atr: float = 0.10
    stop_buffer_atr: float = 0.10
    reward_risk: float = 2.0
    fee_rate: float = 0.00095
    slippage_rate: float = 0.0002
    max_hold_bars: int = 24

def _ema(values, period):
    alpha = 2 / (period + 1)
    out = values[0]
    for v in values[1:]:
        out = alpha * v + (1 - alpha) * out
    return out

def _atr(bars):
    tr = []
    for idx, bar in enumerate(bars):
        prev = bars[idx - 1]["close"] if idx else bar["close"]
        tr.append(max(bar["high"] - bar["low"], abs(bar["high"] - prev), abs(bar["low"] - prev)))
    return sum(tr) / len(tr)

def backtest(bars, config=Config()):
    """Returns simulated trades, net return as fraction of entry not equity."""
    trades = []
    start = max(config.lookback, config.trend_period, config.atr_period) + 1
    i = start
    while i < len(bars) - 1:
        bar = bars[i]
        history = bars[i-config.lookback:i]
        atr = _atr(bars[i-config.atr_period+1:i+1])
        if atr <= 0:
            i += 1
            continue
        ema = _ema([b["close"] for b in bars[i-config.trend_period+1:i+1]], config.trend_period)
        low_level = min(b["low"] for b in history)
        high_level = max(b["high"] for b in history)
        long_signal = bar["low"] < low_level - config.min_sweep_atr * atr and bar["close"] > low_level and bar["close"] > ema
        short_signal = bar["high"] > high_level + config.min_sweep_atr * atr and bar["close"] < high_level and bar["close"] < ema
        if not (long_signal or short_signal):
            i += 1
            continue
        side = "LONG" if long_signal else "SHORT"
        entry_index = i + 1
        raw_entry = bars[entry_index]["open"]
        entry = raw_entry * (1 + config.slippage_rate if side == "LONG" else 1 - config.slippage_rate)
        stop = (bar["low"] - config.stop_buffer_atr * atr) if side == "LONG" else (bar["high"] + config.stop_buffer_atr * atr)
        risk = (entry - stop) if side == "LONG" else (stop - entry)
        if risk <= 0:
            i += 1
            continue
        target = entry + config.reward_risk * risk * (1 if side == "LONG" else -1)
        exit_index = min(entry_index + config.max_hold_bars - 1, len(bars) - 1)
        reason = "TIME"
        exit_raw = bars[exit_index]["close"]
        for j in range(entry_index, exit_index + 1):
            b = bars[j]
            hit_stop = b["low"] <= stop if side == "LONG" else b["high"] >= stop
            hit_target = b["high"] >= target if side == "LONG" else b["low"] <= target
            if hit_stop or hit_target:
                exit_index = j
                reason = "STOP" if hit_stop else "TARGET"
                exit_raw = stop if hit_stop else target
                break
        exit_fill = exit_raw * (1 - config.slippage_rate if side == "LONG" else 1 + config.slippage_rate)
        gross = (exit_fill - entry) / entry * (1 if side == "LONG" else -1)
        net = gross - config.fee_rate * (1 + exit_fill / entry)
        trades.append({"side":side,"signal_index":i,"entry_index":entry_index,"exit_index":exit_index,
                       "entry":entry,"stop":stop,"target":target,"exit":exit_fill,"reason":reason,
                       "gross_return":gross,"net_return":net})
        i = exit_index + 1
    return trades
