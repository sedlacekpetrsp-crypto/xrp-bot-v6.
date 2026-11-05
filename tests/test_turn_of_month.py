"""Mechanika turn-of-month backtestu na syntetických datech (není důkaz ziskovosti)."""
from datetime import date, datetime, timedelta, timezone

import pytest

from research.turn_of_month import run

D0 = datetime(2023, 1, 1, tzinfo=timezone.utc)


def bars(n, f=lambda i: 100.0 + i):
    out = []
    for i in range(n):
        px = f(i)
        out.append({"ts": int((D0 + timedelta(days=i)).timestamp() * 1000),
                    "open": px, "high": px + 1, "low": px - 1, "close": px + 0.5})
    return out


def test_windows_last_two_and_first_three_days():
    w = run.windows(date(2023, 1, 1), date(2023, 4, 30))
    assert w == [(date(2023, 1, 30), date(2023, 2, 3)), (date(2023, 2, 27), date(2023, 3, 3)),
                 (date(2023, 3, 30), date(2023, 4, 3))]
    # okno přes hranici období se nebere
    assert run.windows(date(2023, 1, 1), date(2023, 2, 2)) == []
    assert run.windows(date(2023, 1, 1), date(2023, 2, 28), shift=-10)[0] == (date(2023, 1, 20), date(2023, 1, 24))


def test_entry_open_exit_close_costs_and_equity():
    b = bars(70)
    tr, cv = run.simulate(b, date(2023, 1, 1), date(2023, 3, 10), mult=2, equity=1000.0)
    assert [t["entry_day"] for t in tr] == ["2023-01-30", "2023-02-27"]
    t = tr[0]
    assert t["entry_px"] == pytest.approx((100 + 29) * (1 + 2 * run.SLIP))
    assert t["exit_px"] == pytest.approx((100 + 33 + 0.5) * (1 - 2 * run.SLIP))
    assert t["fees"] == pytest.approx(t["qty"] * (t["entry_px"] + t["exit_px"]) * 2 * run.FEE)
    assert cv[date(2023, 1, 29)] == pytest.approx(1000.0)            # mimo okno hotovost
    assert cv[date(2023, 3, 10)] == pytest.approx(1000.0 + sum(x["net_pnl"] for x in tr))


def test_flat_price_loses_exactly_costs():
    b = bars(70, lambda i: 100.0)
    for x in b:
        x["close"] = 100.0
    tr, _ = run.simulate(b, date(2023, 1, 1), date(2023, 3, 10), mult=1, equity=1000.0)
    assert all(t["net_pnl"] < 0 for t in tr)
    assert all(t["gross_pnl"] < 0 for t in tr)  # skluz


def test_verdict_requires_all_checks():
    m = lambda **k: {"sharpe": 2, "max_drawdown_pct": 5, "trades": 48, "profit_factor": 2, "net_pnl": 100,
                     "net_without_top3": 50, **k}
    bh = {"sharpe": 1, "max_drawdown_pct": 30}
    res = {"strategy": {f"{p}/x{x}": m() for p in run.PERIODS for x in (1, 2, 3)},
           "buy_hold": {f"{p}/x{x}": bh for p in run.PERIODS for x in (1, 2, 3)}}
    assert run.verdict(res)["status"].startswith("KANDID")
    res["strategy"]["final_test/x2"] = m(net_pnl=-1)
    assert run.verdict(res)["status"] == "ZAMÍTNUTO"
