"""Mechanika RSI(2) pullback backtestu na syntetických datech (není důkaz ziskovosti)."""
from datetime import date, datetime, timedelta, timezone

import pytest

from research.rsi2_pullback import run

D0 = datetime(2022, 1, 1, tzinfo=timezone.utc)


def bars(closes):
    out = []
    for i, c in enumerate(closes):
        o = closes[i - 1] if i else c
        out.append({"ts": int((D0 + timedelta(days=i)).timestamp() * 1000),
                    "open": o, "high": max(o, c) + 1, "low": min(o, c) - 1, "close": c})
    return out


def d(i):
    return (D0 + timedelta(days=i)).date()


def test_rsi_and_sma():
    r = run.rsi_wilder([10, 11, 12, 11, 10])
    assert r[:2] == [None, None] and r[2] == 100.0
    # Wilder: ag=(1*1+0)/2=0.5, al=(0+1)/2=0.5 -> 50
    assert r[3] == pytest.approx(50.0)
    assert run.sma([1, 2, 3, 4], 2) == [None, 1.5, 2.5, 3.5]


def test_entry_next_open_exit_next_open_after_close_above_sma5():
    up = [100 + i for i in range(220)]                    # uptrend nad SMA200
    closes = up + [310, 300, 330, 340] + [341] * 10       # prudký pokles -> RSI2 nízké
    b = bars(closes)
    tr, cv = run.simulate(b, d(210), d(len(closes) - 1), mult=1, equity=1000.0)
    t = tr[0]
    assert t["entry_day"] == d(222).isoformat()           # signál na close dne 221, plnění open 222
    assert t["entry_px"] == pytest.approx(b[222]["open"] * (1 + run.SLIP))
    # close dne 222 (330) > SMA5 -> výstup open 223
    assert t["exit_day"] == d(223).isoformat() and t["exit_reason"] == "signal"
    assert t["exit_px"] == pytest.approx(b[223]["open"] * (1 - run.SLIP))
    assert t["fees"] == pytest.approx(t["qty"] * (t["entry_px"] + t["exit_px"]) * run.FEE)
    last = d(len(closes) - 1)
    assert cv[last] == pytest.approx(1000.0 + sum(x["net_pnl"] for x in tr))


def test_trend_filter_blocks_entries_below_sma200():
    down = [400 - i for i in range(260)]
    b = bars(down)
    tr, _ = run.simulate(b, d(210), d(259), mult=1, equity=1000.0)
    assert tr == []
    tr2, _ = run.simulate(b, d(210), d(259), mult=1, equity=1000.0, trend=False)
    assert len(tr2) >= 1


def test_forced_exit_at_period_end_and_flat_loses_costs():
    closes = [100 + i for i in range(220)] + [300, 290, 280, 270, 260]
    b = bars(closes)
    tr, _ = run.simulate(b, d(210), d(224), mult=3, equity=1000.0)
    assert tr[-1]["exit_reason"] == "period_end" and tr[-1]["exit_day"] == d(224).isoformat()
    flat = bars([100.0] * 230)
    trf, _ = run.simulate(flat, d(200), d(229), mult=1, equity=1000.0, trend=False)
    assert all(t["net_pnl"] <= 0 for t in trf)


def test_verdict_requires_all_checks():
    m = lambda **k: {"sharpe": 2, "max_drawdown_pct": 5, "trades": 48, "profit_factor": 2, "net_pnl": 100,
                     "net_without_top3": 50, **k}
    bh = {"sharpe": 1, "max_drawdown_pct": 30}
    res = {"strategy": {f"{p}/x{x}": m() for p in run.PERIODS for x in (1, 2, 3)},
           "buy_hold": {f"{p}/x{x}": bh for p in run.PERIODS for x in (1, 2, 3)}}
    assert run.verdict(res)["status"].startswith("KANDID")
    res["strategy"]["validation/x1"] = m(trades=29)
    assert run.verdict(res)["status"] == "ZAMÍTNUTO"
