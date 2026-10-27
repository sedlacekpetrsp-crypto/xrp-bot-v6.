"""Frozen market-neutral spot/perpetual carry simulator (offline only)."""
from dataclasses import dataclass
from math import isfinite

STEP = 3_600_000


@dataclass(frozen=True)
class Config:
    min_funding: float = 0.00030
    min_premium: float = 0.0010
    stop_widening: float = 0.0150
    max_hold: int = 168
    leg_fraction: float = 0.10
    spot_fee: float = 0.00095
    perp_fee: float = 0.00050
    slippage: float = 0.00020


def validate(bars, funding):
    timestamps = [b["timestamp"] for b in bars]
    if any(t % STEP for t in timestamps) or any(b <= a for a, b in zip(timestamps, timestamps[1:])):
        raise ValueError("bar timestamp")
    for bar in bars:
        for prefix in ("spot", "mark"):
            o, h, l, c = (float(bar[f"{prefix}_{k}"]) for k in ("open", "high", "low", "close"))
            if not all(isfinite(x) for x in (o, h, l, c)) or not 0 < l <= min(o, c) <= max(o, c) <= h:
                raise ValueError(f"{prefix} OHLC")
    ft = [f["timestamp"] for f in funding]
    if any(t % STEP for t in ft) or any(b <= a for a, b in zip(ft, ft[1:])):
        raise ValueError("funding timestamp")
    if any(not isfinite(float(f["rate"])) for f in funding):
        raise ValueError("funding rate")


def premium(bar, field="close"):
    return bar[f"mark_{field}"] / bar[f"spot_{field}"] - 1.0


def _exit_values(bar, c, kind):
    if kind == "STOP":
        raw_spot, raw_mark = bar["spot_low"], bar["mark_high"]
    elif kind == "CLOSE":
        raw_spot, raw_mark = bar["spot_close"], bar["mark_close"]
    else:
        raw_spot, raw_mark = bar["spot_open"], bar["mark_open"]
    return raw_spot, raw_mark, raw_spot * (1 - c.slippage), raw_mark * (1 + c.slippage)


def backtest(bars, funding, start, end, c=Config(), initial=10_000.0):
    """Return non-overlapping closed pair trades and a conservative marked-equity curve."""
    validate(bars, funding)
    funding_by_time = {f["timestamp"]: f["rate"] for f in funding}
    latest_rate, funding_cursor, equity, i = None, 0, initial, 0
    trades, curve = [], [{"timestamp": start, "equity": initial}]
    while i + 1 < len(bars):
        signal = bars[i]
        # Funding is published on nominal bar timestamps. Advancing this cursor to
        # signal time uses only observations known no later than that closed bar.
        while funding_cursor < len(funding) and funding[funding_cursor]["timestamp"] <= signal["timestamp"]:
            latest_rate = funding[funding_cursor]["rate"]
            funding_cursor += 1
        entry_bar = bars[i + 1]
        if signal["timestamp"] < start or entry_bar["timestamp"] >= end:
            i += 1
            continue
        if entry_bar["timestamp"] - signal["timestamp"] != STEP:
            i += 1
            continue
        if latest_rate is None or latest_rate < c.min_funding or premium(signal) < c.min_premium:
            i += 1
            continue

        entry_equity = equity
        leg_notional = equity * c.leg_fraction
        raw_spot_entry, raw_mark_entry = entry_bar["spot_open"], entry_bar["mark_open"]
        spot_entry, mark_entry = raw_spot_entry * (1 + c.slippage), raw_mark_entry * (1 - c.slippage)
        spot_qty, mark_qty = leg_notional / raw_spot_entry, leg_notional / raw_mark_entry
        entry_fees = c.spot_fee * spot_qty * spot_entry + c.perp_fee * mark_qty * mark_entry
        stop_premium = premium(entry_bar, "open") + c.stop_widening
        funding_cash, funding_count = 0.0, 0
        j, closed = i + 1, False
        while j < len(bars) and bars[j]["timestamp"] < end:
            bar = bars[j]
            if j > i + 1 and bar["timestamp"] - bars[j - 1]["timestamp"] != STEP:
                prev = bars[j - 1]
                raw_spot, raw_mark, spot_exit, mark_exit = _exit_values(prev, c, "CLOSE")
                reason, exit_index, exit_time = "DATA_GAP", j - 1, prev["timestamp"]
                closed = True
            else:
                open_premium = premium(bar, "open")
                prior_basis_exit = j > i + 1 and premium(bars[j - 1]) <= 0
                time_exit = j - (i + 1) >= c.max_hold
                if open_premium >= stop_premium:
                    raw_spot, raw_mark, spot_exit, mark_exit = _exit_values(bar, c, "OPEN")
                    reason, exit_index, exit_time = "GAP_STOP", j, bar["timestamp"]
                    closed = True
                elif prior_basis_exit or time_exit:
                    raw_spot, raw_mark, spot_exit, mark_exit = _exit_values(bar, c, "OPEN")
                    reason = "BASIS" if prior_basis_exit else "TIME"
                    exit_index, exit_time, closed = j, bar["timestamp"], True
                elif bar["mark_high"] / bar["spot_low"] - 1.0 >= stop_premium:
                    raw_spot, raw_mark, spot_exit, mark_exit = _exit_values(bar, c, "STOP")
                    reason, exit_index, exit_time = "STOP", j, bar["timestamp"]
                    closed = True

            if closed:
                exit_fees = c.spot_fee * spot_qty * spot_exit + c.perp_fee * mark_qty * mark_exit
                fees = entry_fees + exit_fees
                gross = spot_qty * (raw_spot - raw_spot_entry) + mark_qty * (raw_mark_entry - raw_mark)
                fill_pnl = spot_qty * (spot_exit - spot_entry) + mark_qty * (mark_entry - mark_exit)
                slippage_cost = gross - fill_pnl
                pnl = fill_pnl + funding_cash - fees
                equity += pnl
                trades.append(dict(
                    signal_timestamp=signal["timestamp"], entry_timestamp=entry_bar["timestamp"],
                    exit_timestamp=exit_time, entry_index=i + 1, exit_index=exit_index,
                    entry_equity=entry_equity, leg_notional=leg_notional,
                    raw_spot_entry=raw_spot_entry, raw_mark_entry=raw_mark_entry,
                    raw_spot_exit=raw_spot, raw_mark_exit=raw_mark,
                    spot_entry=spot_entry, mark_entry=mark_entry, spot_exit=spot_exit, mark_exit=mark_exit,
                    spot_qty=spot_qty, mark_qty=mark_qty, entry_premium=premium(entry_bar, "open"),
                    stop_premium=stop_premium, signal_funding_rate=latest_rate,
                    funding_cash=funding_cash, funding_count=funding_count,
                    gross=gross, slippage_cost=slippage_cost, fees=fees, pnl=pnl,
                    equity=equity, reason=reason,
                ))
                curve.append({"timestamp": exit_time, "equity": equity})
                i = exit_index
                break

            # A position exiting at this open does not receive same-timestamp funding.
            if bar["timestamp"] > entry_bar["timestamp"] and bar["timestamp"] in funding_by_time:
                funding_cash += mark_qty * bar["mark_close"] * funding_by_time[bar["timestamp"]]
                funding_count += 1
            hypothetical_spot = bar["spot_low"] * (1 - c.slippage)
            hypothetical_mark = bar["mark_high"] * (1 + c.slippage)
            hypothetical_exit_fees = c.spot_fee * spot_qty * hypothetical_spot + c.perp_fee * mark_qty * hypothetical_mark
            marked = entry_equity + spot_qty * (hypothetical_spot - spot_entry) + mark_qty * (mark_entry - hypothetical_mark) + funding_cash - entry_fees - hypothetical_exit_fees
            curve.append({"timestamp": bar["timestamp"], "equity": marked})
            j += 1
        if not closed:
            last = bars[min(j - 1, len(bars) - 1)]
            raw_spot, raw_mark, spot_exit, mark_exit = _exit_values(last, c, "CLOSE")
            exit_fees = c.spot_fee * spot_qty * spot_exit + c.perp_fee * mark_qty * mark_exit
            fees = entry_fees + exit_fees
            gross = spot_qty * (raw_spot - raw_spot_entry) + mark_qty * (raw_mark_entry - raw_mark)
            fill_pnl = spot_qty * (spot_exit - spot_entry) + mark_qty * (mark_entry - mark_exit)
            slippage_cost = gross - fill_pnl
            pnl = fill_pnl + funding_cash - fees
            equity += pnl
            trades.append(dict(signal_timestamp=signal["timestamp"], entry_timestamp=entry_bar["timestamp"], exit_timestamp=last["timestamp"], entry_index=i+1, exit_index=min(j-1,len(bars)-1), entry_equity=entry_equity, leg_notional=leg_notional, raw_spot_entry=raw_spot_entry, raw_mark_entry=raw_mark_entry, raw_spot_exit=raw_spot, raw_mark_exit=raw_mark, spot_entry=spot_entry, mark_entry=mark_entry, spot_exit=spot_exit, mark_exit=mark_exit, spot_qty=spot_qty, mark_qty=mark_qty, entry_premium=premium(entry_bar,"open"), stop_premium=stop_premium, signal_funding_rate=latest_rate, funding_cash=funding_cash, funding_count=funding_count, gross=gross, slippage_cost=slippage_cost, fees=fees, pnl=pnl, equity=equity, reason="END"))
            curve.append({"timestamp": last["timestamp"], "equity": equity})
            i = min(j - 1, len(bars) - 1)
        i += 1
    return trades, curve

