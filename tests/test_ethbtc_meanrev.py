"""Mechanika mean-reversion ETHBTC (syntetická data, NENÍ důkaz ziskovosti)."""
from datetime import date, datetime, timedelta, timezone

import pytest

from research.ethbtc_meanrev import run


def bars(start, closes, opens=None):
    out = []
    for i, c in enumerate(closes):
        d = start + timedelta(days=i)
        ts = int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)
        o = opens[i] if opens else c
        out.append({"ts": ts, "open": o, "high": max(o, c), "low": min(o, c), "close": c})
    return out


H = date(2022, 12, 1)  # historie pro okno z20
S = date(2023, 1, 1)
PRE = (S - H).days


def mk(btc, eth, ratio, btc_open=None, eth_open=None):
    return {"BTCUSDT": bars(H, btc, btc_open), "ETHUSDT": bars(H, eth, eth_open), "ETHBTC": bars(H, ratio)}


def flat_ratio(n, tail=()):
    base = [0.05 + 0.0001 * ((i % 2) * 2 - 1) for i in range(n - len(tail))]
    return base + list(tail)


def test_zscore_uses_window_including_t():
    r = bars(H, [1.0] * 19 + [2.0])
    z = run.zscores(r)
    assert len(z) == 1
    # mu = 1.05, sd = sqrt(19*0.0025 + 0.9025)/sqrt(20)
    import math
    mu = 1.05
    sd = math.sqrt((19 * (1 - mu) ** 2 + (2 - mu) ** 2) / 20)
    assert z[H + timedelta(days=19)] == pytest.approx((2 - mu) / sd)


def test_state_machine():
    assert run.next_state("N", -2.1) == "E"
    assert run.next_state("N", 2.1) == "B"
    assert run.next_state("N", 1.9) == "N"
    assert run.next_state("E", -0.5) == "E"
    assert run.next_state("E", 0.1) == "N"
    assert run.next_state("B", 0.5) == "B"
    assert run.next_state("B", -0.1) == "N"
    assert run.next_state("E", 3.0) == "N"  # žádný přímý přechod E -> B


def test_flat_no_episode_ledger_sums():
    n = PRE + 10
    m = mk([100.0] * n, [10.0] * n, flat_ratio(n))
    rows, cv = run.simulate(m, S, S + timedelta(days=9), 1)
    assert [r["segment"] for r in rows] == ["N"]
    k = (1 - run.SLIP) * (1 - run.FEE) / ((1 + run.SLIP) * (1 + run.FEE))
    assert cv[max(cv)] == pytest.approx(10_000 * k)
    assert sum(r["net_pnl"] for r in rows) == pytest.approx(cv[max(cv)] - 10_000)


def test_entry_next_open_exit_and_ledger_consistency():
    n = PRE + 8
    # den S+1: poměr spadne (z << -2) -> E za open S+2; den S+4 návrat nad průměr -> N za open S+5
    tail = [0.05, 0.04, 0.04, 0.045, 0.06, 0.06, 0.06, 0.06]
    ratio = flat_ratio(n, tail)
    btc = [100.0] * n
    eth = [10.0] * n
    for i in range(PRE + 3, n):  # ETH roste během epizody a zůstane (výstup za open S+5 = 12)
        eth[i] = 12.0
    eth_open = list(eth)
    eth_open[PRE + 2] = 10.0
    m = mk(btc, eth, ratio, eth_open=eth_open)
    z = run.zscores(m["ETHBTC"])
    assert z[S + timedelta(days=1)] < -2
    rows, cv = run.simulate(m, S, S + timedelta(days=7), 2)
    eps = run.episodes(rows)
    assert len(eps) >= 1
    e = eps[0]
    assert e["segment"] == "E"
    assert e["entry_day"] == (S + timedelta(days=2)).isoformat()  # open dne po signálu
    assert sum(r["net_pnl"] for r in rows) == pytest.approx(cv[max(cv)] - 10_000)
    for r in rows:
        assert r["gross_pnl"] - r["fees"] == pytest.approx(r["net_pnl"])
        assert r["fees"] >= -1e-9
    # ledger je souvislý
    for a, b in zip(rows, rows[1:]):
        assert a["exit_day"] == b["entry_day"]
    # ETH 10 -> 12 během držení 100 % ETH => epizoda zisková i po nákladech
    assert e["net_pnl"] > 0


def test_missing_day_raises():
    n = PRE + 5
    m = mk([100.0] * n, [10.0] * n, flat_ratio(n))
    del m["ETHUSDT"][PRE + 2]
    with pytest.raises(ValueError):
        run.simulate(m, S, S + timedelta(days=4), 1)
