"""Frozen BTC mempool-clearance signal and XRP spot simulator."""
from dataclasses import dataclass
import datetime as dt
import math
import statistics

DAY = 86_400_000
UTC = dt.timezone.utc


@dataclass(frozen=True)
class Config:
    lookback: int = 365
    min_intraday_points: int = 64
    tercile_numerator: int = 1
    tercile_denominator: int = 3
    atr_n: int = 14
    stop_atr: float = 2.0
    reward_r: float = 3.0
    max_hold: int = 5
    risk_fraction: float = 0.005
    notional_cap: float = 0.20
    fee: float = 0.00095
    slippage: float = 0.00020


def aggregate_daily(points, min_points=64):
    """Aggregate unique, ordered intraday observations to UTC-day medians."""
    seen = set()
    grouped = {}
    last = None
    for point in points:
        ts = int(point["timestamp"])
        value = float(point["mempool_bytes"])
        if last is not None and ts <= last:
            raise ValueError("intraday timestamps not strictly increasing")
        if ts in seen:
            raise ValueError("duplicate intraday timestamp")
        if not math.isfinite(value) or value < 0:
            raise ValueError("invalid mempool value")
        last = ts
        seen.add(ts)
        day = ts - ts % DAY
        grouped.setdefault(day, []).append(value)
    out = []
    for day in sorted(grouped):
        values = grouped[day]
        if len(values) < min_points:
            raise ValueError(f"incomplete UTC day {day}: {len(values)}")
        out.append(dict(timestamp=day, mempool_bytes=statistics.median(values), samples=len(values)))
    for a, b in zip(out, out[1:]):
        if b["timestamp"] - a["timestamp"] != DAY:
            raise ValueError("daily metric gap")
    return out


def lower_tercile(window):
    ordered = sorted(float(x) for x in window)
    if not ordered:
        raise ValueError("empty window")
    return ordered[(len(ordered) - 1) // 3]


def make_signals(metric, c=Config()):
    for a, b in zip(metric, metric[1:]):
        if b["timestamp"] - a["timestamp"] != DAY:
            raise ValueError("metric gap")
    out = {}
    for i in range(c.lookback, len(metric)):
        row = metric[i]
        date = dt.datetime.fromtimestamp(row["timestamp"] / 1000, UTC)
        if date.weekday() != 4:  # Friday only
            continue
        window = [x["mempool_bytes"] for x in metric[i - c.lookback : i]]
        cutoff = lower_tercile(window)
        current = float(row["mempool_bytes"])
        if current <= cutoff:
            entry = row["timestamp"] + 3 * DAY  # Monday; 48h after Friday closes
            out[entry] = dict(
                metric_timestamp=row["timestamp"],
                mempool_bytes=current,
                cutoff365=cutoff,
                samples=int(row["samples"]),
            )
    return out


def validate(rows):
    for i, row in enumerate(rows):
        if i and row["timestamp"] - rows[i - 1]["timestamp"] != DAY:
            raise ValueError("price gap")
        if not 0 < row["low"] <= min(row["open"], row["close"]) <= max(row["open"], row["close"]) <= row["high"]:
            raise ValueError("OHLC")


def atr(rows, i, n):
    if i < n + 1:
        return None
    return sum(
        max(
            rows[j]["high"] - rows[j]["low"],
            abs(rows[j]["high"] - rows[j - 1]["close"]),
            abs(rows[j]["low"] - rows[j - 1]["close"]),
        )
        for j in range(i - n, i)
    ) / n


def backtest(rows, start, end, c=Config(), initial=10_000.0):
    validate(rows)
    equity = initial
    trades = []
    curve = [dict(timestamp=start, equity=initial)]
    i = 0
    while i < len(rows):
        bar = rows[i]
        signal = bar.get("mempool_signal")
        av = atr(rows, i, c.atr_n)
        if not signal or not (start <= bar["timestamp"] < end) or av is None or signal["metric_timestamp"] + 3 * DAY != bar["timestamp"]:
            i += 1
            continue
        if dt.datetime.fromtimestamp(bar["timestamp"] / 1000, UTC).weekday() != 0:
            raise ValueError("entry is not Monday")
        raw_entry = bar["open"]
        entry = raw_entry * (1 + c.slippage)
        stop = entry - c.stop_atr * av
        if stop <= 0:
            i += 1
            continue
        qty = min(equity * c.risk_fraction / (entry - stop), equity * c.notional_cap / entry)
        target = entry + c.reward_r * (entry - stop)
        entry_fee = qty * entry * c.fee
        before = equity
        j = i
        while j < len(rows) and rows[j]["timestamp"] < end:
            x = rows[j]
            if j > i and x["timestamp"] - rows[j - 1]["timestamp"] != DAY:
                raw_exit, reason, ei, et = rows[j - 1]["close"], "DATA_GAP", j - 1, rows[j - 1]["timestamp"]
            elif x["open"] <= stop:
                raw_exit, reason, ei, et = x["open"], "GAP_STOP", j, x["timestamp"]
            elif x["low"] <= stop:
                raw_exit, reason, ei, et = stop, "STOP", j, x["timestamp"]
            elif x["open"] >= target or x["high"] >= target:
                raw_exit, reason, ei, et = target, "TARGET", j, x["timestamp"]
            elif j - i + 1 >= c.max_hold:
                raw_exit, reason, ei, et = x["close"], "TIME", j, x["timestamp"]
            else:
                mark = x["low"] * (1 - c.slippage)
                curve.append(dict(timestamp=x["timestamp"], equity=before + qty * (mark - entry) - entry_fee - qty * mark * c.fee))
                j += 1
                continue
            fill = raw_exit * (1 - c.slippage)
            exit_fee = qty * fill * c.fee
            gross = qty * (raw_exit - raw_entry)
            fill_pnl = qty * (fill - entry)
            fees = entry_fee + exit_fee
            pnl = fill_pnl - fees
            equity += pnl
            trades.append(
                dict(
                    metric_timestamp=signal["metric_timestamp"],
                    entry_timestamp=bar["timestamp"], exit_timestamp=et,
                    entry_index=i, exit_index=ei, entry_equity=before,
                    mempool_bytes=signal["mempool_bytes"], cutoff365=signal["cutoff365"], samples=signal["samples"],
                    raw_entry=raw_entry, raw_exit=raw_exit, entry=entry, exit=fill,
                    qty=qty, atr=av, stop=stop, target=target, leg_notional=qty * entry,
                    gross=gross, slippage_cost=gross - fill_pnl, fees=fees, pnl=pnl,
                    equity=equity, reason=reason, cost_fee=c.fee, cost_slippage=c.slippage,
                )
            )
            curve.append(dict(timestamp=et, equity=equity))
            i = ei + 1
            break
        else:
            # A chronological fold must not silently discard a still-open trade.
            # Liquidate at the last real candle before the fold boundary.
            ei = min(j - 1, len(rows) - 1)
            if ei < i:
                i += 1
                continue
            et = rows[ei]["timestamp"]
            raw_exit = rows[ei]["close"]
            reason = "FOLD_END"
            fill = raw_exit * (1 - c.slippage)
            exit_fee = qty * fill * c.fee
            gross = qty * (raw_exit - raw_entry)
            fill_pnl = qty * (fill - entry)
            fees = entry_fee + exit_fee
            pnl = fill_pnl - fees
            equity += pnl
            trades.append(
                dict(
                    metric_timestamp=signal["metric_timestamp"],
                    entry_timestamp=bar["timestamp"], exit_timestamp=et,
                    entry_index=i, exit_index=ei, entry_equity=before,
                    mempool_bytes=signal["mempool_bytes"], cutoff365=signal["cutoff365"], samples=signal["samples"],
                    raw_entry=raw_entry, raw_exit=raw_exit, entry=entry, exit=fill,
                    qty=qty, atr=av, stop=stop, target=target, leg_notional=qty * entry,
                    gross=gross, slippage_cost=gross - fill_pnl, fees=fees, pnl=pnl,
                    equity=equity, reason=reason, cost_fee=c.fee, cost_slippage=c.slippage,
                )
            )
            curve.append(dict(timestamp=et, equity=equity))
            i = ei + 1
    return trades, curve
