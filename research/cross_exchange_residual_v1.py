"""Frozen cross-exchange residual convergence simulator (offline only)."""
from dataclasses import dataclass
from math import isfinite

STEP = 3_600_000


@dataclass(frozen=True)
class Config:
    enter_residual: float = -0.0075
    exit_residual: float = -0.0010
    stop_residual: float = -0.0175
    max_hold: int = 72
    leg_fraction: float = 0.10
    coinbase_fee: float = 0.0060
    binance_fee: float = 0.0005
    coinbase_slippage: float = 0.0010
    binance_slippage: float = 0.0003


def validate(bars, funding):
    ts = [b["timestamp"] for b in bars]
    if any(t % STEP for t in ts) or any(b <= a for a, b in zip(ts, ts[1:])):
        raise ValueError("bar timestamp")
    for bar in bars:
        for p in ("cxrp", "bxrp", "cbtc", "bbtc"):
            o, h, l, c = (float(bar[f"{p}_{k}"]) for k in ("open", "high", "low", "close"))
            if not all(isfinite(x) for x in (o, h, l, c)) or not 0 < l <= min(o, c) <= max(o, c) <= h:
                raise ValueError(f"{p} OHLC")
    ft = [f["timestamp"] for f in funding]
    if any(t % STEP for t in ft) or any(b <= a for a, b in zip(ft, ft[1:])):
        raise ValueError("funding timestamp")


def residual(bar, field="close"):
    return (bar[f"cxrp_{field}"] / bar[f"bxrp_{field}"]) / (bar[f"cbtc_{field}"] / bar[f"bbtc_{field}"]) - 1.0


def adverse_residual(bar):
    return (bar["cxrp_low"] / bar["bxrp_high"]) / (bar["cbtc_high"] / bar["bbtc_low"]) - 1.0


def backtest(bars, funding, start, end, c=Config(), initial=10_000.0):
    validate(bars, funding)
    funding_by_time = {x["timestamp"]: float(x["rate"]) for x in funding}
    equity, trades, curve, i = initial, [], [{"timestamp": start, "equity": initial}], 0
    while i + 1 < len(bars):
        signal, entry_bar = bars[i], bars[i + 1]
        if signal["timestamp"] < start or entry_bar["timestamp"] >= end or entry_bar["timestamp"] - signal["timestamp"] != STEP or residual(signal) > c.enter_residual:
            i += 1; continue
        entry_equity = equity
        notional = equity * c.leg_fraction
        raw_c_entry, raw_b_entry = entry_bar["cxrp_open"], entry_bar["bxrp_open"]
        c_entry = raw_c_entry * (1 + c.coinbase_slippage)
        b_entry = raw_b_entry * (1 - c.binance_slippage)
        c_qty, b_qty = notional / raw_c_entry, notional / raw_b_entry
        entry_fees = c.coinbase_fee * c_qty * c_entry + c.binance_fee * b_qty * b_entry
        funding_cash, funding_count, j, closed = 0.0, 0, i + 1, False
        while j < len(bars) and bars[j]["timestamp"] < end:
            bar = bars[j]
            kind = None
            if j > i + 1 and bar["timestamp"] - bars[j - 1]["timestamp"] != STEP:
                exit_bar, kind, exit_time, exit_index, use = bars[j - 1], "DATA_GAP", bars[j - 1]["timestamp"], j - 1, "close"
            elif residual(bar, "open") <= c.stop_residual:
                exit_bar, kind, exit_time, exit_index, use = bar, "GAP_STOP", bar["timestamp"], j, "open"
            elif adverse_residual(bar) <= c.stop_residual:
                exit_bar, kind, exit_time, exit_index, use = bar, "STOP", bar["timestamp"], j, "adverse"
            elif j > i + 1 and residual(bars[j - 1]) >= c.exit_residual:
                exit_bar, kind, exit_time, exit_index, use = bar, "CONVERGENCE", bar["timestamp"], j, "open"
            elif j - (i + 1) >= c.max_hold:
                exit_bar, kind, exit_time, exit_index, use = bar, "TIME", bar["timestamp"], j, "open"
            if kind:
                if use == "adverse": raw_c_exit, raw_b_exit = exit_bar["cxrp_low"], exit_bar["bxrp_high"]
                else: raw_c_exit, raw_b_exit = exit_bar[f"cxrp_{use}"], exit_bar[f"bxrp_{use}"]
                c_exit = raw_c_exit * (1 - c.coinbase_slippage)
                b_exit = raw_b_exit * (1 + c.binance_slippage)
                exit_fees = c.coinbase_fee * c_qty * c_exit + c.binance_fee * b_qty * b_exit
                fees = entry_fees + exit_fees
                gross = c_qty * (raw_c_exit - raw_c_entry) + b_qty * (raw_b_entry - raw_b_exit)
                fill = c_qty * (c_exit - c_entry) + b_qty * (b_entry - b_exit)
                pnl = fill + funding_cash - fees
                equity += pnl
                trades.append(dict(signal_timestamp=signal["timestamp"],entry_timestamp=entry_bar["timestamp"],exit_timestamp=exit_time,entry_index=i+1,exit_index=exit_index,entry_equity=entry_equity,leg_notional=notional,raw_coinbase_entry=raw_c_entry,raw_binance_entry=raw_b_entry,raw_coinbase_exit=raw_c_exit,raw_binance_exit=raw_b_exit,coinbase_entry=c_entry,binance_entry=b_entry,coinbase_exit=c_exit,binance_exit=b_exit,coinbase_qty=c_qty,binance_qty=b_qty,signal_residual=residual(signal),entry_residual=residual(entry_bar,"open"),funding_cash=funding_cash,funding_count=funding_count,gross=gross,slippage_cost=gross-fill,fees=fees,pnl=pnl,equity=equity,reason=kind))
                curve.append({"timestamp":exit_time,"equity":equity}); i = exit_index; closed = True; break
            if bar["timestamp"] > entry_bar["timestamp"] and bar["timestamp"] in funding_by_time:
                funding_cash += b_qty * bar["bxrp_close"] * funding_by_time[bar["timestamp"]]
                funding_count += 1
            c_mark = bar["cxrp_low"] * (1-c.coinbase_slippage); b_mark = bar["bxrp_high"] * (1+c.binance_slippage)
            marked = entry_equity + c_qty*(c_mark-c_entry) + b_qty*(b_entry-b_mark) + funding_cash - entry_fees - c.coinbase_fee*c_qty*c_mark - c.binance_fee*b_qty*b_mark
            curve.append({"timestamp":bar["timestamp"],"equity":marked}); j += 1
        if not closed:
            break
        i += 1
    return trades, curve
