"""Mechanika SMA200 overlay backtestu na syntetických datech (není důkaz ziskovosti)."""
from datetime import datetime, timedelta, timezone

import pytest

from research.sma200_overlay import run

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


def test_enters_first_day_when_prior_close_above_and_exits_next_open_after_cross_down():
    closes = [100 + i for i in range(250)] + [100] * 20      # uptrend, pak pád pod SMA200 v den 250
    b = bars(closes)
    tr, cv = run.simulate(b, d(240), d(len(closes) - 1), mult=1, equity=1000.0)
    t = tr[0]
    assert t["entry_day"] == d(240).isoformat()
    assert t["entry_px"] == pytest.approx(b[240]["open"] * (1 + run.SLIP))
    assert t["exit_day"] == d(251).isoformat() and t["exit_reason"] == "signal"
    assert t["exit_px"] == pytest.approx(b[251]["open"] * (1 - run.SLIP))
    assert len(tr) == 1
    assert t["net_pnl"] == pytest.approx(t["gross_pnl"] - t["fees"])
    assert cv[d(len(closes) - 1)] == pytest.approx(1000.0 + t["net_pnl"])


def test_no_position_below_sma_and_forced_close_at_end():
    closes = [300 - i for i in range(230)] + [400] * 5
    b = bars(closes)
    tr, _ = run.simulate(b, d(210), d(len(closes) - 1), mult=1, equity=1000.0)
    assert len(tr) == 1
    assert tr[0]["entry_day"] == d(231).isoformat()        # close dne 230 > SMA -> open 231
    assert tr[0]["exit_reason"] == "period_end" and tr[0]["exit_day"] == d(234).isoformat()


def test_band_reduces_whipsaw():
    base = [100.0] * 210
    wiggle = [101, 99.5, 101, 99.5, 101, 99.5]
    b = bars(base + wiggle + [100] * 3)
    t0, _ = run.simulate(b, d(205), d(len(b) - 1), mult=1, equity=1000.0)
    t2, _ = run.simulate(b, d(205), d(len(b) - 1), mult=1, equity=1000.0, band=0.02)
    assert len(t0) >= 3 and len(t2) == 0


def test_costs_scale():
    closes = [100 + i for i in range(250)] + [100] * 5
    b = bars(closes)
    t1, _ = run.simulate(b, d(240), d(254), mult=1, equity=1000.0)
    t3, _ = run.simulate(b, d(240), d(254), mult=3, equity=1000.0)
    assert t3[0]["fees"] > 2.9 * t1[0]["fees"] * 0.95 and t3[0]["net_pnl"] < t1[0]["net_pnl"]
