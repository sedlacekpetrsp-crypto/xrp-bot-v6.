#!/usr/bin/env python3
"""
Backtest of the PUBLICLY DESCRIBED Blue Whale-style BTC logic.

This is deliberately an approximation, not a reconstruction of VIP signals.
Rules are fixed before the test:
- 1H liquidity sweep of a rolling high/low.
- Close back inside the swept level.
- Reversal confirmation within N bars.
- Higher-timeframe (4H) market-structure filter using EMA20/EMA50.
- Stop beyond sweep extreme + buffer.
- Fixed net risk sizing (0.30% equity).
- Simulated fee 0.05%/side + slippage 0.02%/side.
- No overlapping positions.
- Walk-forward split: first 70% train, last 30% test.

A candidate only "passes" if OUT-OF-SAMPLE:
- net PnL > 0
- profit factor >= 1.15
- at least 20 trades
- max drawdown <= 10%
"""
from __future__ import annotations

import json
import math
import os
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

SYMBOL = "BTCUSDT"
API = "https://data-api.binance.vision/api/v3/klines"
START_EQUITY = 10_000.0
RISK_FRACTION = 0.003
FEE = 0.0005
SLIPPAGE = 0.0002
ROUND_TRIP_COST = 2 * (FEE + SLIPPAGE)
STOP_BUFFER = 0.001
MAX_HOLD_BARS = 24
MIN_STOP = 0.002
MAX_STOP = 0.05

@dataclass
class Bar:
    t: int
    o: float
    h: float
    l: float
    c: float
    v: float

def ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)

def fetch_klines(interval: str, start_ms: int, end_ms: int) -> list[Bar]:
    out: list[Bar] = []
    cursor = start_ms
    while cursor < end_ms:
        qs = urllib.parse.urlencode({
            "symbol": SYMBOL,
            "interval": interval,
            "startTime": cursor,
            "endTime": end_ms,
            "limit": 1000,
        })
        req = urllib.request.Request(API + "?" + qs, headers={"User-Agent": "blue-whale-backtest/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            rows = json.loads(r.read().decode("utf-8"))
        if not rows:
            break
        for x in rows:
            out.append(Bar(int(x[0]), float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5])))
        nxt = int(rows[-1][0]) + 1
        if nxt <= cursor:
            break
        cursor = nxt
        time.sleep(0.05)
    dedup = {b.t: b for b in out}
    return [dedup[k] for k in sorted(dedup)]

def ema(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    alpha = 2.0 / (period + 1)
    out = [values[0]]
    for x in values[1:]:
        out.append(alpha * x + (1 - alpha) * out[-1])
    return out

def htf_trend_map(bars4h: list[Bar]) -> dict[int, int]:
    closes = [b.c for b in bars4h]
    e20 = ema(closes, 20)
    e50 = ema(closes, 50)
    # keyed by 4h open time; +1 bull, -1 bear, 0 weak/unknown
    m = {}
    for i, b in enumerate(bars4h):
        if i < 50:
            m[b.t] = 0
            continue
        spread = abs(e20[i] - e50[i]) / b.c
        if spread < 0.001:
            m[b.t] = 0
        else:
            m[b.t] = 1 if e20[i] > e50[i] else -1
    return m

def trend_for(t: int, tmap: dict[int, int]) -> int:
    bucket = t - (t % (4 * 60 * 60 * 1000))
    # use prior CLOSED 4h bar to avoid lookahead
    return tmap.get(bucket - 4 * 60 * 60 * 1000, 0)

def candidate_signals(bars: list[Bar], tmap: dict[int, int], lookback: int, confirm_bars: int):
    sigs = []
    i = max(lookback, 2)
    while i < len(bars) - confirm_bars - 1:
        b = bars[i]
        prior = bars[i-lookback:i]
        low_level = min(x.l for x in prior)
        high_level = max(x.h for x in prior)
        tr = trend_for(b.t, tmap)

        side = None
        swept_level = None
        if tr == 1 and b.l < low_level and b.c > low_level:
            side = "LONG"
            swept_level = low_level
        elif tr == -1 and b.h > high_level and b.c < high_level:
            side = "SHORT"
            swept_level = high_level

        if side:
            # sweep candle must reject meaningfully back into range
            rng = max(b.h - b.l, 1e-12)
            rejection_ok = ((b.c - b.l) / rng >= 0.55) if side == "LONG" else ((b.h - b.c) / rng >= 0.55)
            if rejection_ok:
                confirm_idx = None
                for j in range(i + 1, min(i + 1 + confirm_bars, len(bars))):
                    c = bars[j]
                    if side == "LONG" and c.c > b.h and c.c > c.o:
                        confirm_idx = j
                        break
                    if side == "SHORT" and c.c < b.l and c.c < c.o:
                        confirm_idx = j
                        break
                if confirm_idx is not None:
                    sigs.append((confirm_idx, side, i, swept_level))
                    i = confirm_idx
        i += 1
    return sigs

def run_bt(bars: list[Bar], tmap: dict[int, int], start_i: int, end_i: int,
           lookback: int, confirm_bars: int, rr: float):
    signals = candidate_signals(bars, tmap, lookback, confirm_bars)
    signals = [s for s in signals if start_i <= s[0] < end_i]
    equity = START_EQUITY
    peak = equity
    max_dd = 0.0
    gross_wins = 0.0
    gross_losses = 0.0
    trades = []
    next_free = start_i

    for entry_i, side, sweep_i, _ in signals:
        if entry_i < next_free or entry_i >= end_i - 1:
            continue
        ebar = bars[entry_i]
        sweep = bars[sweep_i]
        market_entry = ebar.c
        entry = market_entry * (1 + SLIPPAGE if side == "LONG" else 1 - SLIPPAGE)
        if side == "LONG":
            stop = sweep.l * (1 - STOP_BUFFER)
            stop_rate = (entry - stop) / entry
        else:
            stop = sweep.h * (1 + STOP_BUFFER)
            stop_rate = (stop - entry) / entry
        if not (MIN_STOP <= stop_rate <= MAX_STOP):
            continue

        # Risk sizing includes estimated round-trip friction.
        effective_stop_rate = stop_rate + ROUND_TRIP_COST
        risk_dollars = equity * RISK_FRACTION
        notional = risk_dollars / effective_stop_rate
        qty = notional / entry
        target_distance = rr * effective_stop_rate
        target = entry * (1 + target_distance) if side == "LONG" else entry * (1 - target_distance)

        exit_i = min(entry_i + MAX_HOLD_BARS, end_i - 1)
        exit_market = bars[exit_i].c
        reason = "TIME"

        for k in range(entry_i + 1, exit_i + 1):
            x = bars[k]
            if side == "LONG":
                hit_sl = x.l <= stop
                hit_tp = x.h >= target
            else:
                hit_sl = x.h >= stop
                hit_tp = x.l <= target
            # Conservative same-bar tie: assume stop first.
            if hit_sl:
                exit_i, exit_market, reason = k, stop, "SL"
                break
            if hit_tp:
                exit_i, exit_market, reason = k, target, "TP"
                break

        exit_px = exit_market * (1 - SLIPPAGE if side == "LONG" else 1 + SLIPPAGE)
        gross = (exit_px - entry) * qty if side == "LONG" else (entry - exit_px) * qty
        fees = (entry + exit_px) * qty * FEE
        pnl = gross - fees
        equity += pnl
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak - equity) / peak if peak > 0 else 0)
        if pnl >= 0:
            gross_wins += pnl
        else:
            gross_losses += -pnl
        trades.append({
            "side": side, "entry_t": bars[entry_i].t, "exit_t": bars[exit_i].t,
            "pnl": pnl, "reason": reason,
        })
        next_free = exit_i + 1

    wins = sum(1 for t in trades if t["pnl"] > 0)
    losses = sum(1 for t in trades if t["pnl"] < 0)
    pf = gross_wins / gross_losses if gross_losses > 0 else (999.0 if gross_wins > 0 else 0.0)
    return {
        "trades": len(trades),
        "wins": wins,
        "losses": losses,
        "winrate": wins / len(trades) if trades else 0.0,
        "net_pnl": equity - START_EQUITY,
        "return_pct": (equity / START_EQUITY - 1) * 100,
        "profit_factor": pf,
        "max_drawdown_pct": max_dd * 100,
        "ending_equity": equity,
    }

def main():
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=540)
    print(f"Fetching {SYMBOL} data {start.isoformat()} -> {now.isoformat()}", flush=True)
    bars1h = fetch_klines("1h", ms(start), ms(now))
    bars4h = fetch_klines("4h", ms(start - timedelta(days=10)), ms(now))
    if len(bars1h) < 5000 or len(bars4h) < 1000:
        raise RuntimeError(f"Insufficient market data: 1h={len(bars1h)} 4h={len(bars4h)}")
    tmap = htf_trend_map(bars4h)

    split = int(len(bars1h) * 0.70)
    grid = []
    for lookback in (12, 20, 24, 36):
        for confirm in (1, 2, 3):
            for rr in (1.0, 1.5, 2.0):
                train = run_bt(bars1h, tmap, 100, split, lookback, confirm, rr)
                if train["trades"] >= 30:
                    score = train["profit_factor"] - 0.02 * train["max_drawdown_pct"]
                    grid.append((score, lookback, confirm, rr, train))
    if not grid:
        raise RuntimeError("No parameter set produced enough training trades")
    grid.sort(key=lambda x: x[0], reverse=True)
    _, lookback, confirm, rr, train = grid[0]
    test = run_bt(bars1h, tmap, split, len(bars1h), lookback, confirm, rr)

    passed = (
        test["net_pnl"] > 0
        and test["profit_factor"] >= 1.15
        and test["trades"] >= 20
        and test["max_drawdown_pct"] <= 10.0
    )
    result = {
        "strategy": "public_blue_whale_approx_v1",
        "symbol": SYMBOL,
        "data_bars_1h": len(bars1h),
        "data_bars_4h": len(bars4h),
        "train_fraction": 0.70,
        "selected": {"lookback": lookback, "confirm_bars": confirm, "rr": rr},
        "train": train,
        "test": test,
        "pass_criteria": {
            "net_pnl_positive": True,
            "profit_factor_min": 1.15,
            "trades_min": 20,
            "max_drawdown_pct_max": 10.0,
        },
        "passed": passed,
        "note": "Approximation of public concepts only; not VIP signal reconstruction.",
    }
    print("RESULT_JSON=" + json.dumps(result, sort_keys=True), flush=True)

if __name__ == "__main__":
    main()
