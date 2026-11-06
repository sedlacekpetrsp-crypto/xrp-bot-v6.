"""Mechanika pásmového rebalance (syntetická data, NENÍ důkaz ziskovosti)."""
from datetime import date, datetime, timedelta, timezone

import pytest

from research.rebalance_band import run


def bars(start, closes, opens=None):
    out = []
    for i, c in enumerate(closes):
        d = start + timedelta(days=i)
        ts = int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)
        o = opens[i] if opens else c
        out.append({"ts": ts, "open": o, "high": max(o, c), "low": min(o, c), "close": c})
    return out


S = date(2023, 1, 1)


def mk(btc, eth, btc_open=None, eth_open=None):
    return {"BTCUSDT": bars(S, btc, btc_open), "ETHUSDT": bars(S, eth, eth_open)}


def test_flat_prices_no_rebalance_costs_only():
    m = mk([100.0] * 10, [10.0] * 10)
    tr, cv, nr = run.simulate(m, S, S + timedelta(days=9), 1)
    assert nr == 0 and len(tr) == 2
    k = (1 - run.SLIP) * (1 - run.FEE) / ((1 + run.SLIP) * (1 + run.FEE))
    assert cv[max(cv)] == pytest.approx(10_000 * k)
    assert sum(t["net_pnl"] for t in tr) == pytest.approx(cv[max(cv)] - 10_000)


def test_band_triggers_next_open_and_restores_50_50():
    btc = [100.0, 100.0, 130.0, 130.0, 130.0]  # w_BTC k close dne 2 = 130/230 = 0,565 > 0,55
    eth = [10.0] * 5
    m = mk(btc, eth)
    tr, cv, nr = run.simulate(m, S, S + timedelta(days=4), 2)
    assert nr == 1
    rb = [t for t in tr if t["exit_reason"].startswith("rebalance")]
    assert {t["exit_day"] for t in rb} == {(S + timedelta(days=3)).isoformat()}  # open dne 3
    after = [t for t in tr if t["entry_day"] == (S + timedelta(days=3)).isoformat()]
    assert len(after) == 2
    assert after[0]["start_value"] == pytest.approx(after[1]["start_value"])
    assert sum(t["net_pnl"] for t in tr) == pytest.approx(cv[max(cv)] - 10_000)
    for t in tr:
        assert t["gross_pnl"] - t["fees"] == pytest.approx(t["net_pnl"])
        assert t["fees"] >= 0


def test_within_band_no_trade():
    m = mk([100.0, 100.0, 120.0, 120.0], [10.0] * 4)  # 120/220 = 0,545 < 0,55
    _, _, nr = run.simulate(m, S, S + timedelta(days=3), 1)
    assert nr == 0


def test_no_lookahead_uses_open_prices():
    # signál k close dne 1, obchod za open dne 2 (open se liší od close)
    m = mk([100.0, 140.0, 140.0], [10.0] * 3, btc_open=[100.0, 100.0, 120.0])
    tr, _, nr = run.simulate(m, S, S + timedelta(days=2), 1)
    assert nr == 1
    rb = [t for t in tr if t["exit_reason"].startswith("rebalance") and t["symbol"] == "BTCUSDT"][0]
    assert rb["exit_px"] == 120.0 and rb["exit_day"] == (S + timedelta(days=2)).isoformat()


def test_monthly_variant_rebalances_on_first_day():
    start = date(2023, 1, 30)
    n = 5
    m = {"BTCUSDT": bars(start, [100.0 + i for i in range(n)]), "ETHUSDT": bars(start, [10.0] * n)}
    _, _, nr = run.simulate(m, start, start + timedelta(days=n - 1), 1, "monthly")
    assert nr == 1  # 2023-02-01


def test_ledger_sum_matches_equity_random_walk():
    import random
    rnd = random.Random(7)
    b, e = [100.0], [10.0]
    for _ in range(199):
        b.append(b[-1] * (1 + rnd.gauss(0, 0.04)))
        e.append(e[-1] * (1 + rnd.gauss(0, 0.05)))
    m = mk(b, e, btc_open=[x * 1.003 for x in b], eth_open=[x * 0.997 for x in e])
    for mult in (1, 3):
        tr, cv, nr = run.simulate(m, S, S + timedelta(days=199), mult)
        assert nr > 3
        assert sum(t["net_pnl"] for t in tr) == pytest.approx(cv[max(cv)] - 10_000)
        assert len(tr) == 2 * (nr + 1)


def test_missing_day_raises():
    m = mk([100.0] * 5, [10.0] * 5)
    del m["ETHUSDT"][2]
    with pytest.raises(ValueError):
        run.simulate(m, S, S + timedelta(days=4), 1)
