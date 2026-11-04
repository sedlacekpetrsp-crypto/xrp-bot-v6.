"""Frozen XRP reverse-repo liquidity-release simulator; offline only."""
from dataclasses import dataclass
from math import isfinite

DAY = 86_400_000


@dataclass(frozen=True)
class Config:
    macro_lookback: int = 20
    release_lag: int = 2
    minimum_start_balance: float = 100.0
    maximum_change: float = -0.10
    atr_n: int = 14
    stop_atr: float = 2.0
    reward_r: float = 3.0
    max_hold: int = 5
    risk_fraction: float = 0.005
    notional_cap: float = 0.20
    fee: float = 0.00095
    slippage: float = 0.00020


def validate_prices(rows):
    times = [x["timestamp"] for x in rows]
    if any(t % DAY for t in times) or any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("timestamp")
    for x in rows:
        o, h, l, c = (float(x[k]) for k in ("open", "high", "low", "close"))
        if not all(isfinite(v) for v in (o, h, l, c)) or not 0 < l <= min(o, c) <= max(o, c) <= h:
            raise ValueError("price")


def make_signals(macro, config=Config()):
    """Map a lagged RRP release to the second subsequent actual observation."""
    times = [x["timestamp"] for x in macro]
    if any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("macro timestamp")
    if any(not isfinite(float(x["value"])) or float(x["value"]) < 0 for x in macro):
        raise ValueError("macro value")
    out = {}
    first = config.release_lag + config.macro_lookback
    for eligible in range(first, len(macro)):
        latest_i = eligible - config.release_lag
        earlier_i = latest_i - config.macro_lookback
        latest = float(macro[latest_i]["value"])
        earlier = float(macro[earlier_i]["value"])
        if earlier <= 0:
            continue
        change = latest / earlier - 1.0
        if earlier >= config.minimum_start_balance and change <= config.maximum_change:
            out[macro[eligible]["timestamp"]] = dict(
                metric_timestamp=macro[latest_i]["timestamp"],
                earlier_timestamp=macro[earlier_i]["timestamp"],
                latest_balance=latest,
                earlier_balance=earlier,
                rrp_change=change,
            )
    return out


def signal_at(rows, i):
    if i + 1 >= len(rows) or rows[i + 1]["timestamp"] - rows[i]["timestamp"] != DAY:
        return False
    return bool(rows[i].get("macro_signal"))


def atr(rows, i, n):
    if i < n:
        return None
    if any(rows[j]["timestamp"] - rows[j - 1]["timestamp"] != DAY for j in range(i - n + 1, i + 1)):
        return None
    values = []
    for j in range(i - n + 1, i + 1):
        previous = rows[j - 1]["close"]
        values.append(max(rows[j]["high"] - rows[j]["low"], abs(rows[j]["high"] - previous), abs(rows[j]["low"] - previous)))
    return sum(values) / n


def backtest(rows, start, end, config=Config(), initial=10_000.0):
    validate_prices(rows)
    equity, trades = initial, []
    curve = [{"timestamp": start, "equity": initial}]
    i = 0
    while i + 1 < len(rows):
        signal, entry_bar = rows[i], rows[i + 1]
        a = atr(rows, i, config.atr_n)
        if signal["timestamp"] < start or entry_bar["timestamp"] >= end or a is None or not signal_at(rows, i):
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
        entry_fee, entry_equity = qty * entry * config.fee, equity
        j, closed = i + 1, False
        while j < len(rows) and rows[j]["timestamp"] < end:
            bar = rows[j]
            if j > i + 1 and bar["timestamp"] - rows[j - 1]["timestamp"] != DAY:
                raw_exit, reason, exit_i, exit_time = rows[j - 1]["close"], "DATA_GAP", j - 1, rows[j - 1]["timestamp"]
            elif bar["open"] <= stop:
                raw_exit, reason, exit_i, exit_time = bar["open"], "GAP_STOP", j, bar["timestamp"]
            elif bar["low"] <= stop:
                raw_exit, reason, exit_i, exit_time = stop, "STOP", j, bar["timestamp"]
            elif bar["open"] >= target or bar["high"] >= target:
                raw_exit, reason, exit_i, exit_time = target, "TARGET", j, bar["timestamp"]
            elif j - (i + 1) >= config.max_hold:
                raw_exit, reason, exit_i, exit_time = bar["open"], "TIME", j, bar["timestamp"]
            else:
                mark = bar["low"] * (1 - config.slippage)
                curve.append({"timestamp": bar["timestamp"], "equity": entry_equity + qty * (mark - entry) - entry_fee - qty * mark * config.fee})
                j += 1
                continue
            exit_fill = raw_exit * (1 - config.slippage)
            exit_fee = qty * exit_fill * config.fee
            gross = qty * (raw_exit - raw_entry)
            fill_pnl = qty * (exit_fill - entry)
            fees = entry_fee + exit_fee
            pnl = fill_pnl - fees
            equity += pnl
            trades.append(dict(
                signal_timestamp=signal["timestamp"], metric_timestamp=signal["metric_timestamp"],
                earlier_timestamp=signal["earlier_timestamp"], entry_timestamp=entry_bar["timestamp"],
                exit_timestamp=exit_time, entry_index=i + 1, exit_index=exit_i, entry_equity=entry_equity,
                raw_entry=raw_entry, raw_exit=raw_exit, entry=entry, exit=exit_fill, qty=qty, atr=a,
                stop=stop, target=target, earlier_balance=signal["earlier_balance"],
                latest_balance=signal["latest_balance"], rrp_change=signal["rrp_change"],
                leg_notional=qty * entry, gross=gross, slippage_cost=gross - fill_pnl,
                fees=fees, pnl=pnl, equity=equity, reason=reason,
            ))
            curve.append({"timestamp": exit_time, "equity": equity})
            i, closed = exit_i, True
            break
        if not closed:
            exit_i = min(j - 1, len(rows) - 1)
            bar = rows[exit_i]
            raw_exit = bar["close"]
            exit_fill = raw_exit * (1 - config.slippage)
            exit_fee = qty * exit_fill * config.fee
            gross = qty * (raw_exit - raw_entry)
            fill_pnl = qty * (exit_fill - entry)
            fees = entry_fee + exit_fee
            pnl = fill_pnl - fees
            equity += pnl
            trades.append(dict(
                signal_timestamp=signal["timestamp"], metric_timestamp=signal["metric_timestamp"],
                earlier_timestamp=signal["earlier_timestamp"], entry_timestamp=entry_bar["timestamp"],
                exit_timestamp=bar["timestamp"], entry_index=i + 1, exit_index=exit_i,
                entry_equity=entry_equity, raw_entry=raw_entry, raw_exit=raw_exit, entry=entry,
                exit=exit_fill, qty=qty, atr=a, stop=stop, target=target,
                earlier_balance=signal["earlier_balance"], latest_balance=signal["latest_balance"],
                rrp_change=signal["rrp_change"], leg_notional=qty * entry, gross=gross,
                slippage_cost=gross - fill_pnl, fees=fees, pnl=pnl, equity=equity, reason="END",
            ))
            curve.append({"timestamp": bar["timestamp"], "equity": equity})
            i = exit_i
        i += 1
    return trades, curve

