"""Causal, fixed-parameter XRP volatility-compression breakout (offline only)."""
from dataclasses import dataclass
from math import isfinite

STEP = 3_600_000


@dataclass(frozen=True)
class Config:
    atr_window: int = 24
    percentile_window: int = 720
    compression_quantile: float = 0.20
    breakout_window: int = 72
    stop_atr: float = 2.0
    target_r: float = 3.0
    max_hold: int = 72
    fee: float = 0.00095
    slippage: float = 0.00020
    risk: float = 0.005
    notional_cap: float = 0.20


def validate(bars):
    ts = [b["timestamp"] for b in bars]
    if not ts or any(t % STEP for t in ts) or any(b <= a for a, b in zip(ts, ts[1:])):
        raise ValueError("timestamp")
    for b in bars:
        o, h, l, c = (float(b[k]) for k in ("open", "high", "low", "close"))
        if not all(isfinite(x) for x in (o, h, l, c)) or not 0 < l <= min(o, c) <= max(o, c) <= h:
            raise ValueError("OHLC")


def percentile(values, q):
    values = sorted(values)
    rank = q * (len(values) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(values) - 1)
    weight = rank - lo
    return values[lo] * (1 - weight) + values[hi] * weight


def indicators(bars, c=Config()):
    validate(bars)
    atrs = [None] * len(bars)
    natrs = [None] * len(bars)
    for i in range(c.atr_window, len(bars)):
        if bars[i]["timestamp"] - bars[i - c.atr_window]["timestamp"] != c.atr_window * STEP:
            continue
        ranges = []
        for k in range(i - c.atr_window + 1, i + 1):
            ranges.append(max(bars[k]["high"] - bars[k]["low"], abs(bars[k]["high"] - bars[k - 1]["close"]), abs(bars[k]["low"] - bars[k - 1]["close"])))
        atrs[i] = sum(ranges) / c.atr_window
        natrs[i] = atrs[i] / bars[i]["close"]
    return atrs, natrs


def signal(bars, atrs, natrs, i, c=Config()):
    earliest = i - c.percentile_window - c.atr_window - 1
    if i < max(c.breakout_window, c.percentile_window + c.atr_window + 1) or earliest < 0:
        return None
    if bars[i]["timestamp"] - bars[earliest]["timestamp"] != (i - earliest) * STEP:
        return None
    compression = natrs[i - 1]
    history = natrs[i - c.percentile_window - 1 : i - 1]
    if compression is None or len(history) != c.percentile_window or any(x is None for x in history):
        return None
    threshold = percentile(history, c.compression_quantile)
    prior_high = max(b["high"] for b in bars[i - c.breakout_window : i])
    if compression > threshold or bars[i]["close"] <= prior_high:
        return None
    return {"atr": atrs[i - 1], "compression_natr": compression, "compression_threshold": threshold, "prior_high": prior_high}


def backtest(bars, start, end, c=Config(), initial=10_000.0):
    validate(bars)
    atrs, natrs = indicators(bars, c)
    equity, out = initial, []
    i = max(c.breakout_window, c.percentile_window + c.atr_window + 1)
    while i + 1 < len(bars):
        if bars[i + 1]["timestamp"] < start:
            i += 1
            continue
        if bars[i + 1]["timestamp"] >= end:
            break
        found = signal(bars, atrs, natrs, i, c)
        if found is None or bars[i + 1]["timestamp"] - bars[i]["timestamp"] != STEP:
            i += 1
            continue
        ei = i + 1
        raw_entry = bars[ei]["open"]
        entry = raw_entry * (1 + c.slippage)
        stop = entry - c.stop_atr * found["atr"]
        if stop <= 0 or entry <= stop:
            i += 1
            continue
        target = entry + c.target_r * (entry - stop)
        qty = min(equity * c.risk / (entry - stop), equity * c.notional_cap / entry)
        raw_exit, reason, xi = None, None, ei
        for held in range(c.max_hold):
            j = ei + held
            if j >= len(bars) or bars[j]["timestamp"] >= end:
                break
            if j > ei and bars[j]["timestamp"] - bars[j - 1]["timestamp"] != STEP:
                xi, raw_exit, reason = j - 1, bars[j - 1]["close"], "DATA_GAP"
                break
            b = bars[j]
            xi = j
            if b["open"] <= stop:
                raw_exit, reason = b["open"], "GAP_STOP"
                break
            if b["low"] <= stop:
                raw_exit, reason = stop, "STOP"
                break
            if b["high"] >= target:
                raw_exit, reason = target, "TARGET"
                break
            if held + 1 == c.max_hold:
                raw_exit, reason = b["close"], "TIME"
                break
        if raw_exit is None:
            xi = max(ei, min(xi, len(bars) - 1))
            raw_exit, reason = bars[xi]["close"], "END"
        fill = raw_exit * (1 - c.slippage)
        fees = c.fee * qty * (entry + fill)
        gross = qty * (raw_exit - raw_entry)
        pnl = qty * (fill - entry) - fees
        equity += pnl
        out.append(dict(signal_index=i, entry_index=ei, exit_index=xi, entry=entry, exit=fill, raw_entry=raw_entry, raw_exit=raw_exit, stop=stop, target=target, qty=qty, pnl=pnl, equity=equity, fees=fees, gross=gross, slippage_cost=gross - fees - pnl, reason=reason, **found))
        if equity <= 0:
            break
        i = xi + 1
    return out

