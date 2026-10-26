"""Causal cross-sectional crypto breadth capitulation signal for XRP spot."""
from dataclasses import dataclass
from math import isfinite
from statistics import median

STEP = 3_600_000


@dataclass(frozen=True)
class Config:
    lookback: int = 6
    members_down: int = 6
    member_drop: float = -0.02
    median_drop: float = -0.02
    xrp_drop: float = -0.025
    atr_window: int = 24
    stop_atr: float = 1.5
    target_r: float = 2.0
    max_hold: int = 24
    fee: float = 0.00095
    slippage: float = 0.0002
    risk: float = 0.005
    notional_cap: float = 0.20


def validate_series(bars):
    timestamps = [b["timestamp"] for b in bars]
    if any(t % STEP for t in timestamps) or any(b <= a for a, b in zip(timestamps, timestamps[1:])):
        raise ValueError("timestamp")
    for bar in bars:
        o, h, l, c = (float(bar[k]) for k in ("open", "high", "low", "close"))
        if not all(isfinite(x) for x in (o, h, l, c)) or not 0 < l <= min(o, c) <= max(o, c) <= h:
            raise ValueError("OHLC")


def signal(xrp, basket_maps, i, c=Config()):
    if i < max(c.lookback, c.atr_window):
        return None
    timestamp = xrp[i]["timestamp"]
    prior_timestamp = timestamp - c.lookback * STEP
    if xrp[i-c.lookback]["timestamp"] != prior_timestamp:
        return None
    returns = []
    for market in basket_maps.values():
        current, previous = market.get(timestamp), market.get(prior_timestamp)
        if current is None or previous is None:
            return None
        returns.append(current/previous-1)
    xrp_return = xrp[i]["close"]/xrp[i-c.lookback]["close"]-1
    breadth_count = sum(value <= c.member_drop for value in returns)
    breadth_median = median(returns)
    if breadth_count < c.members_down or breadth_median > c.median_drop or xrp_return > c.xrp_drop:
        return None
    if xrp[i]["timestamp"] - xrp[i-c.atr_window]["timestamp"] != c.atr_window * STEP:
        return None
    true_ranges = [
        max(
            xrp[k]["high"]-xrp[k]["low"],
            abs(xrp[k]["high"]-xrp[k-1]["close"]),
            abs(xrp[k]["low"]-xrp[k-1]["close"]),
        )
        for k in range(i-c.atr_window+1, i+1)
    ]
    atr = sum(true_ranges)/len(true_ranges)
    return dict(atr=atr, xrp_return=xrp_return, breadth_count=breadth_count, breadth_median=breadth_median) if atr > 0 else None


def backtest(xrp, basket, start, end, c=Config(), initial=10_000.0):
    validate_series(xrp)
    for bars in basket.values():
        validate_series(bars)
    maps = {symbol: {bar["timestamp"]: bar["close"] for bar in bars} for symbol, bars in basket.items()}
    output, equity = [], initial
    i = max(c.lookback, c.atr_window)
    while i < len(xrp)-1:
        if xrp[i+1]["timestamp"] < start:
            i += 1
            continue
        if xrp[i+1]["timestamp"] >= end:
            break
        if xrp[i+1]["timestamp"] != xrp[i]["timestamp"] + STEP:
            i += 1
            continue
        found = signal(xrp, maps, i, c)
        if found is None:
            i += 1
            continue
        entry_index = i+1
        entry = xrp[entry_index]["open"]*(1+c.slippage)
        stop = entry-c.stop_atr*found["atr"]
        if stop <= 0:
            i += 1
            continue
        qty = min(equity*c.risk/(entry-stop), equity*c.notional_cap/entry)
        target = entry+c.target_r*(entry-stop)
        exit_index = entry_index
        while exit_index+1 < len(xrp) and exit_index-entry_index+1 < c.max_hold and xrp[exit_index+1]["timestamp"] < end and xrp[exit_index+1]["timestamp"] == xrp[exit_index]["timestamp"]+STEP:
            exit_index += 1
        raw, reason = xrp[exit_index]["close"], "TIME"
        for j in range(entry_index, exit_index+1):
            bar = xrp[j]
            if bar["open"] <= stop:
                exit_index, raw, reason = j, bar["open"], "GAP_STOP"
                break
            if bar["low"] <= stop:
                exit_index, raw, reason = j, stop, "STOP"
                break
            if bar["high"] >= target:
                exit_index, raw, reason = j, target, "TARGET"
                break
        fill = raw*(1-c.slippage)
        fees = c.fee*qty*(entry+fill)
        gross = qty*(raw-entry/(1+c.slippage))
        pnl = qty*(fill-entry)-fees
        equity += pnl
        output.append(dict(
            signal_index=i, entry_index=entry_index, exit_index=exit_index,
            entry=entry, exit=fill, stop=stop, target=target, qty=qty,
            pnl=pnl, equity=equity, fees=fees, gross=gross,
            slippage_cost=gross-fees-pnl, reason=reason,
            xrp_return=found["xrp_return"], breadth_count=found["breadth_count"],
            breadth_median=found["breadth_median"],
        ))
        if equity <= 0:
            break
        i = exit_index+1
    return output
