"""Causal funding-dislocation signal with spot-only execution."""
from dataclasses import dataclass
from math import isfinite

STEP = 3_600_000


@dataclass(frozen=True)
class Config:
    funding_window: int = 90
    quantile: float = 0.10
    absolute_ceiling: float = 0.0
    atr_window: int = 24
    stop_atr: float = 1.5
    target_r: float = 2.0
    max_hold: int = 12
    fee: float = 0.00095
    slippage: float = 0.0002
    risk: float = 0.005
    notional_cap: float = 0.20


def validate(bars, funding):
    bt = [b["timestamp"] for b in bars]
    ft = [f["timestamp"] for f in funding]
    for seq in (bt, ft):
        if any(t % STEP for t in seq) or any(b <= a for a, b in zip(seq, seq[1:])):
            raise ValueError("timestamp")
    for b in bars:
        o, h, l, c = (float(b[k]) for k in ("open", "high", "low", "close"))
        if not all(isfinite(x) for x in (o, h, l, c)) or not 0 < l <= min(o, c) <= max(o, c) <= h:
            raise ValueError("OHLC")
    for f in funding:
        if not isfinite(float(f["rate"])) or int(f["interval_hours"]) <= 0:
            raise ValueError("funding")


def _quantile(values, q):
    ordered = sorted(values)
    rank = q * (len(ordered) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(ordered) - 1)
    weight = rank - lo
    return ordered[lo] * (1 - weight) + ordered[hi] * weight


def funding_signal(funding, i, c=Config()):
    if i < c.funding_window:
        return None
    history = funding[i - c.funding_window : i]
    chain = history + [funding[i]]
    for left, right in zip(chain, chain[1:]):
        if right["timestamp"] - left["timestamp"] != int(left["interval_hours"]) * STEP:
            return None
    threshold = _quantile([f["rate"] for f in history], c.quantile)
    rate = funding[i]["rate"]
    if rate >= c.absolute_ceiling or rate > threshold:
        return None
    return {"funding_rate": rate, "rolling_threshold": threshold}


def backtest(bars, funding, start, end, c=Config(), initial=10_000.0):
    validate(bars, funding)
    by_time = {b["timestamp"]: (i, b) for i, b in enumerate(bars)}
    out, equity, last_exit_time = [], initial, -1
    for fi in range(c.funding_window, len(funding)):
        sig = funding_signal(funding, fi, c)
        if sig is None:
            continue
        signal_time = funding[fi]["timestamp"]
        entry_time = signal_time + STEP
        if entry_time < start or entry_time >= end or entry_time <= last_exit_time:
            continue
        located = by_time.get(entry_time)
        signal_bar = by_time.get(signal_time)
        if located is None or signal_bar is None:
            continue
        ei, _ = located
        si, _ = signal_bar
        if si < c.atr_window or bars[si]["timestamp"] - bars[si - c.atr_window]["timestamp"] != c.atr_window * STEP:
            continue
        true_ranges = [
            max(
                bars[k]["high"] - bars[k]["low"],
                abs(bars[k]["high"] - bars[k - 1]["close"]),
                abs(bars[k]["low"] - bars[k - 1]["close"]),
            )
            for k in range(si - c.atr_window + 1, si + 1)
        ]
        atr = sum(true_ranges) / len(true_ranges)
        entry = bars[ei]["open"] * (1 + c.slippage)
        stop = entry - c.stop_atr * atr
        if atr <= 0 or stop <= 0:
            continue
        qty = min(equity * c.risk / (entry - stop), equity * c.notional_cap / entry)
        target = entry + c.target_r * (entry - stop)
        xi = ei
        while xi + 1 < len(bars) and xi - ei + 1 < c.max_hold and bars[xi + 1]["timestamp"] < end and bars[xi + 1]["timestamp"] == bars[xi]["timestamp"] + STEP:
            xi += 1
        raw, reason = bars[xi]["close"], "TIME"
        for j in range(ei, xi + 1):
            b = bars[j]
            if b["open"] <= stop:
                xi, raw, reason = j, b["open"], "GAP_STOP"
                break
            if b["low"] <= stop:
                xi, raw, reason = j, stop, "STOP"
                break
            if b["high"] >= target:
                xi, raw, reason = j, target, "TARGET"
                break
        fill = raw * (1 - c.slippage)
        fees = c.fee * qty * (entry + fill)
        gross = qty * (raw - entry / (1 + c.slippage))
        pnl = qty * (fill - entry) - fees
        equity += pnl
        out.append(
            dict(
                signal_timestamp=signal_time,
                entry_index=ei,
                exit_index=xi,
                entry=entry,
                exit=fill,
                stop=stop,
                target=target,
                qty=qty,
                pnl=pnl,
                equity=equity,
                fees=fees,
                gross=gross,
                slippage_cost=gross - fees - pnl,
                reason=reason,
                funding_rate=sig["funding_rate"],
                rolling_threshold=sig["rolling_threshold"],
            )
        )
        last_exit_time = bars[xi]["timestamp"]
        if equity <= 0:
            break
    return out
