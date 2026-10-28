"""Frozen XRP holder-growth divergence simulator (offline only)."""
from dataclasses import dataclass
from math import isfinite

DAY = 86_400_000


@dataclass(frozen=True)
class Config:
    divergence_days: int = 30
    min_holder_growth: float = 0.01
    max_price_return: float = -0.10
    atr_n: int = 14
    stop_atr: float = 2.0
    reward_r: float = 3.0
    max_hold: int = 30
    risk_fraction: float = 0.005
    notional_cap: float = 0.20
    fee: float = 0.00095
    slippage: float = 0.00020


def validate(rows):
    times = [x["timestamp"] for x in rows]
    if any(t % DAY for t in times) or any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("timestamp")
    for x in rows:
        o, h, l, c = (float(x[k]) for k in ("open", "high", "low", "close"))
        holders = float(x["holders"])
        if not all(isfinite(v) for v in (o, h, l, c, holders)):
            raise ValueError("finite")
        if not 0 < l <= min(o, c) <= max(o, c) <= h or holders <= 0:
            raise ValueError("values")


def signal_at(rows, i, config=Config()):
    """At close i, only metric i-1 may be used; entry is i+1 open."""
    d = config.divergence_days
    if i < d + 1 or i + 1 >= len(rows):
        return False
    window = rows[i - d - 1:i + 2]
    if any(b["timestamp"] - a["timestamp"] != DAY for a, b in zip(window, window[1:])):
        return False
    holder_growth = rows[i - 1]["holders"] / rows[i - d - 1]["holders"] - 1
    price_return = rows[i]["close"] / rows[i - d]["close"] - 1
    return holder_growth >= config.min_holder_growth and price_return <= config.max_price_return


def atr(rows, i, n):
    if i < n:
        return None
    values = []
    for j in range(i - n + 1, i + 1):
        p = rows[j - 1]["close"]
        values.append(max(rows[j]["high"] - rows[j]["low"], abs(rows[j]["high"] - p), abs(rows[j]["low"] - p)))
    return sum(values) / n


def backtest(rows, start, end, config=Config(), initial=10_000.0):
    validate(rows)
    equity = initial
    trades = []
    curve = [{"timestamp": start, "equity": initial}]
    i = 0
    while i + 1 < len(rows):
        signal, entry_bar = rows[i], rows[i + 1]
        a = atr(rows, i, config.atr_n)
        if signal["timestamp"] < start or entry_bar["timestamp"] >= end or a is None or not signal_at(rows, i, config):
            i += 1
            continue
        raw_entry = entry_bar["open"]
        entry = raw_entry * (1 + config.slippage)
        stop = entry - config.stop_atr * a
        if stop <= 0:
            i += 1
            continue
        qty = min(equity * config.risk_fraction / (entry - stop), equity * config.notional_cap / entry)
        target = entry + config.reward_r * (entry - stop)
        entry_fee = qty * entry * config.fee
        entry_equity = equity
        j = i + 1
        closed = False
        while j < len(rows) and rows[j]["timestamp"] < end:
            b = rows[j]
            if j > i + 1 and b["timestamp"] - rows[j - 1]["timestamp"] != DAY:
                raw_exit, reason, exit_i, exit_time = rows[j - 1]["close"], "DATA_GAP", j - 1, rows[j - 1]["timestamp"]
            elif b["open"] <= stop:
                raw_exit, reason, exit_i, exit_time = b["open"], "GAP_STOP", j, b["timestamp"]
            elif b["low"] <= stop:
                raw_exit, reason, exit_i, exit_time = stop, "STOP", j, b["timestamp"]
            elif b["high"] >= target:
                raw_exit, reason, exit_i, exit_time = target, "TARGET", j, b["timestamp"]
            elif j - (i + 1) >= config.max_hold:
                raw_exit, reason, exit_i, exit_time = b["open"], "TIME", j, b["timestamp"]
            else:
                mark = b["low"] * (1 - config.slippage)
                curve.append({"timestamp": b["timestamp"], "equity": entry_equity + qty * (mark - entry) - entry_fee - qty * mark * config.fee})
                j += 1
                continue
            exit_fill = raw_exit * (1 - config.slippage)
            exit_fee = qty * exit_fill * config.fee
            gross = qty * (raw_exit - raw_entry)
            fill_pnl = qty * (exit_fill - entry)
            fees = entry_fee + exit_fee
            pnl = fill_pnl - fees
            equity += pnl
            d = config.divergence_days
            trades.append(dict(signal_timestamp=signal["timestamp"], metric_timestamp=rows[i - 1]["timestamp"], entry_timestamp=entry_bar["timestamp"], exit_timestamp=exit_time, entry_index=i + 1, exit_index=exit_i, entry_equity=entry_equity, raw_entry=raw_entry, raw_exit=raw_exit, entry=entry, exit=exit_fill, qty=qty, atr=a, stop=stop, target=target, signal_holder_growth=rows[i - 1]["holders"] / rows[i - d - 1]["holders"] - 1, signal_price_return=rows[i]["close"] / rows[i - d]["close"] - 1, leg_notional=qty * entry, gross=gross, slippage_cost=gross - fill_pnl, fees=fees, pnl=pnl, equity=equity, reason=reason))
            curve.append({"timestamp": exit_time, "equity": equity})
            i, closed = exit_i, True
            break
        if not closed:
            exit_i = min(j - 1, len(rows) - 1)
            b = rows[exit_i]
            raw_exit = b["close"]
            exit_fill = raw_exit * (1 - config.slippage)
            exit_fee = qty * exit_fill * config.fee
            gross = qty * (raw_exit - raw_entry)
            fill_pnl = qty * (exit_fill - entry)
            fees = entry_fee + exit_fee
            pnl = fill_pnl - fees
            equity += pnl
            d = config.divergence_days
            trades.append(dict(signal_timestamp=signal["timestamp"], metric_timestamp=rows[i - 1]["timestamp"], entry_timestamp=entry_bar["timestamp"], exit_timestamp=b["timestamp"], entry_index=i + 1, exit_index=exit_i, entry_equity=entry_equity, raw_entry=raw_entry, raw_exit=raw_exit, entry=entry, exit=exit_fill, qty=qty, atr=a, stop=stop, target=target, signal_holder_growth=rows[i - 1]["holders"] / rows[i - d - 1]["holders"] - 1, signal_price_return=rows[i]["close"] / rows[i - d]["close"] - 1, leg_notional=qty * entry, gross=gross, slippage_cost=gross - fill_pnl, fees=fees, pnl=pnl, equity=equity, reason="END"))
            curve.append({"timestamp": b["timestamp"], "equity": equity})
            i = exit_i
        i += 1
    return trades, curve
