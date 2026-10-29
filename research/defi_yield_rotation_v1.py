"""Frozen DEFI_YIELD_ROTATION_XRP_V1 simulator; research/offline only."""
from dataclasses import dataclass
from math import isfinite
from statistics import median

DAY = 86_400_000


@dataclass(frozen=True)
class Config:
    yield_lookback: int = 30
    yield_change_lag: int = 7
    max_yield_change_pp: float = -0.50
    atr_n: int = 14
    stop_atr: float = 2.0
    reward_r: float = 3.0
    max_hold: int = 10
    risk_fraction: float = 0.005
    notional_cap: float = 0.20
    fee: float = 0.00095
    slippage: float = 0.00020


def validate_prices(rows):
    times = [x["timestamp"] for x in rows]
    if any(t % DAY for t in times) or any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("price timestamp")
    for x in rows:
        o, h, l, c = (float(x[k]) for k in ("open", "high", "low", "close"))
        if not all(isfinite(v) for v in (o, h, l, c)) or not 0 < l <= min(o, c) <= max(o, c) <= h:
            raise ValueError("price value")


def make_yield_signals(rows, config=Config()):
    """Return source-timestamped signals using only each prefix through that row."""
    times = [x["timestamp"] for x in rows]
    if any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("yield timestamp")
    values = [float(x["apy"]) for x in rows]
    if any(not isfinite(v) or v < 0 for v in values):
        raise ValueError("yield value")
    out = []
    for i in range(config.yield_lookback - 1, len(rows)):
        window = values[i - config.yield_lookback + 1 : i + 1]
        change = values[i] - values[i - config.yield_change_lag]
        if values[i] <= median(window) and change <= config.max_yield_change_pp:
            out.append(dict(source_timestamp=times[i], apy=values[i], median_30=median(window), change_7_pp=change))
    return out


def atr(rows, entry_i, n):
    """ATR ending at entry_i-1; requires an unbroken daily warmup."""
    if entry_i < n + 1:
        return None
    start = entry_i - n
    if any(rows[j]["timestamp"] - rows[j - 1]["timestamp"] != DAY for j in range(start, entry_i)):
        return None
    values = []
    for j in range(start, entry_i):
        prev = rows[j - 1]["close"]
        values.append(max(rows[j]["high"] - rows[j]["low"], abs(rows[j]["high"] - prev), abs(rows[j]["low"] - prev)))
    return sum(values) / n


def backtest(rows, start, end, config=Config(), initial=10_000.0):
    validate_prices(rows)
    equity, trades = initial, []
    curve = [{"timestamp": start, "equity": initial}]
    i = 0
    while i < len(rows):
        bar = rows[i]
        signal = bar.get("yield_signal")
        a = atr(rows, i, config.atr_n)
        if not signal or not (start <= bar["timestamp"] < end) or a is None or signal["source_timestamp"] >= bar["timestamp"]:
            i += 1
            continue
        raw_entry = bar["open"]
        entry = raw_entry * (1 + config.slippage)
        stop = entry - config.stop_atr * a
        if stop <= 0:
            i += 1
            continue
        qty = min(equity * config.risk_fraction / (entry - stop), equity * config.notional_cap / entry)
        target = entry + config.reward_r * (entry - stop)
        entry_fee = qty * entry * config.fee
        entry_equity = equity
        j = i
        while j < len(rows) and rows[j]["timestamp"] < end:
            b = rows[j]
            if j > i and b["timestamp"] - rows[j - 1]["timestamp"] != DAY:
                raw_exit, reason, exit_i, exit_time = rows[j - 1]["close"], "DATA_GAP", j - 1, rows[j - 1]["timestamp"]
            elif b["open"] <= stop:
                raw_exit, reason, exit_i, exit_time = b["open"], "GAP_STOP", j, b["timestamp"]
            elif b["low"] <= stop:
                raw_exit, reason, exit_i, exit_time = stop, "STOP", j, b["timestamp"]
            elif b["open"] >= target or b["high"] >= target:
                raw_exit, reason, exit_i, exit_time = target, "TARGET", j, b["timestamp"]
            elif j - i + 1 >= config.max_hold:
                raw_exit, reason, exit_i, exit_time = b["close"], "TIME", j, b["timestamp"]
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
            trades.append(dict(signal_timestamp=signal["source_timestamp"], entry_timestamp=bar["timestamp"], exit_timestamp=exit_time,
                entry_index=i, exit_index=exit_i, entry_equity=entry_equity, raw_entry=raw_entry, raw_exit=raw_exit,
                entry=entry, exit=exit_fill, qty=qty, atr=a, stop=stop, target=target, apy=signal["apy"],
                median_30=signal["median_30"], change_7_pp=signal["change_7_pp"], leg_notional=qty * entry,
                gross=gross, slippage_cost=gross - fill_pnl, fees=fees, pnl=pnl, equity=equity, reason=reason))
            curve.append({"timestamp": exit_time, "equity": equity})
            i = exit_i + 1
            break
        else:
            i += 1
    return trades, curve
