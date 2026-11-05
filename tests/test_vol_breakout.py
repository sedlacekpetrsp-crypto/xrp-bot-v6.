"""Mechanika vol-breakout backtestu na syntetických datech (není důkaz ziskovosti)."""
from datetime import datetime, timedelta, timezone

import pytest

from research.vol_breakout import run

D0 = datetime(2022, 1, 1, tzinfo=timezone.utc)


def mk(rows):
    return [{"ts": int((D0 + timedelta(days=i)).timestamp() * 1000), "open": o, "high": h, "low": l, "close": c}
            for i, (o, h, l, c) in enumerate(rows)]


def d(i):
    return (D0 + timedelta(days=i)).date()


def test_trigger_entry_and_same_day_exit():
    b = mk([(100, 110, 90, 100), (100, 115, 99, 112), (100, 104, 99, 101)])
    tr, cv = run.simulate(b, d(1), d(2), mult=1, equity=1000.0)
    assert len(tr) == 1                                   # den 2: T = 100 + 0.5*16 = 108 > high 104
    t = tr[0]
    assert t["entry_day"] == t["exit_day"] == d(1).isoformat()
    assert t["entry_px"] == pytest.approx(110 * (1 + run.SLIP))   # T = 100 + 0.5*20
    assert t["exit_px"] == pytest.approx(112 * (1 - run.SLIP))
    assert t["net_pnl"] == pytest.approx(t["gross_pnl"] - t["fees"])
    assert cv[d(2)] == pytest.approx(1000.0 + t["net_pnl"])


def test_no_lookahead_first_bar_and_period_bounds():
    b = mk([(100, 200, 100, 150), (100, 101, 99, 100)])
    tr, cv = run.simulate(b, d(0), d(1), mult=1, equity=1000.0)
    assert tr == [] and cv[d(1)] == 1000.0               # den 0 nemá předchozí bar


def test_losing_day_and_cost_scaling():
    b = mk([(100, 110, 90, 100), (100, 111, 95, 96)])
    t1, _ = run.simulate(b, d(1), d(1), mult=1, equity=1000.0)
    t3, _ = run.simulate(b, d(1), d(1), mult=3, equity=1000.0)
    assert t1[0]["net_pnl"] < 0 and t3[0]["net_pnl"] < t1[0]["net_pnl"]
    assert t3[0]["fees"] > 2.5 * t1[0]["fees"]


def test_sma_filter_blocks_in_downtrend():
    rows = [(300 - i, 302 - i, 298 - i, 300 - i) for i in range(205)] + [(95, 200, 94, 150)]
    b = mk(rows)
    t_plain, _ = run.simulate(b, d(205), d(205), mult=1, equity=1000.0)
    t_f, _ = run.simulate(b, d(205), d(205), mult=1, equity=1000.0, sma_filter=200)
    assert len(t_plain) == 1 and t_f == []


def test_compounding_full_sleeve():
    b = mk([(100, 110, 90, 100), (100, 120, 99, 120), (100, 140, 99, 130)])
    tr, cv = run.simulate(b, d(1), d(2), mult=0, equity=1000.0)
    assert len(tr) == 2
    assert tr[1]["qty"] * tr[1]["entry_px"] == pytest.approx(1000.0 + tr[0]["net_pnl"])
