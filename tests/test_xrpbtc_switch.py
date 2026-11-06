"""Mechanika přepínání BTC<->XRP (syntetická data, NENÍ důkaz ziskovosti)."""
from datetime import date, datetime, timedelta, timezone

import pytest

from research.xrpbtc_switch import run


def bars(start, closes, opens=None):
    out = []
    for i, c in enumerate(closes):
        d = start + timedelta(days=i)
        ts = int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)
        o = opens[i] if opens else c
        out.append({"ts": ts, "open": o, "high": max(o, c), "low": min(o, c), "close": c})
    return out


S = date(2023, 1, 1)


def market(xrpbtc, btc=None, xrp=None, n=None):
    n = n or len(xrpbtc)
    return {"XRPBTC": bars(S, xrpbtc), "BTCUSDT": bars(S, btc or [100.0] * n), "XRPUSDT": bars(S, xrp or [10.0] * n)}


def test_target_sma():
    ec = {S + timedelta(days=i): float(v) for i, v in enumerate([1, 1, 1, 2])}
    assert run.target(ec, S + timedelta(days=3), 4) == "XRP"
    assert run.target(ec, S + timedelta(days=2), 3) == "BTC"  # close == SMA ⇒ BTC
    with pytest.raises(ValueError):
        run.target(ec, S + timedelta(days=3), 5)


def test_no_switch_flat_prices_costs_only():
    m = market([1.0] * 10)
    tr, cv = run.simulate(m, S + timedelta(days=3), S + timedelta(days=9), 1, n=3)
    assert len(tr) == 1 and tr[0]["symbol"] == "BTCUSDT"
    expected = 10_000 * (1 - run.SLIP) / (1 + run.SLIP) / (1 + run.FEE) * (1 - run.FEE)
    assert tr[0]["end_value"] == pytest.approx(expected)
    assert sum(t["net_pnl"] for t in tr) == pytest.approx(cv[max(cv)] - 10_000)


def test_switch_uses_next_open_and_ledger_sums():
    eb = [1.0] * 5 + [2.0 + i for i in range(5)]
    m = market(eb, btc=[100.0 + i for i in range(10)], xrp=[10.0 + i for i in range(10)])
    tr, cv = run.simulate(m, S + timedelta(days=3), S + timedelta(days=9), 2, n=3)
    assert [t["symbol"] for t in tr] == ["BTCUSDT", "XRPUSDT"]
    assert tr[0]["exit_day"] == (S + timedelta(days=6)).isoformat()  # signál close den 5 ⇒ open den 6
    assert tr[1]["entry_day"] == tr[0]["exit_day"]
    assert tr[1]["start_value"] == pytest.approx(tr[0]["end_value"])
    assert sum(t["net_pnl"] for t in tr) == pytest.approx(cv[max(cv)] - 10_000)
    for t in tr:
        assert t["gross_pnl"] - t["fees"] == pytest.approx(t["net_pnl"])


def test_missing_day_raises():
    m = market([1.0] * 10)
    del m["XRPUSDT"][6]
    with pytest.raises(ValueError):
        run.simulate(m, S + timedelta(days=3), S + timedelta(days=9), 1, n=3)
