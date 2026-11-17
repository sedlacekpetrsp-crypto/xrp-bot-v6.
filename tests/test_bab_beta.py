"""Mechanika R11 BAB (syntetická data, NE důkaz ziskovosti)."""
import math
import random
from datetime import date, timedelta

import pytest

from research.bab_beta import run as R


def synth(seed=1, start=date(2020, 1, 1), end=date(2026, 10, 31), betas=None, missing=()):
    rnd = random.Random(seed)
    betas = betas or {a: 0.5 + 0.2 * i for i, a in enumerate(R.ASSETS)}
    px = {a: 100.0 for a in R.ASSETS}
    market = {a: {} for a in R.ASSETS}
    funding = {a: [] for a in R.ASSETS}
    d = start
    while d <= end:
        m = rnd.gauss(0, 0.03)
        for a in R.ASSETS:
            o = px[a]
            c = o * math.exp(betas[a] * m + rnd.gauss(0, 0.01))
            if (a, d) not in missing:
                market[a][d] = (o, max(o, c) * 1.01, min(o, c) * 0.99, c)
            px[a] = c
            for hh in (0, 8, 16):
                funding[a].append((R.day_ms(d) + hh * 3_600_000, 0.0001))
        d += timedelta(days=1)
    return market, funding


@pytest.fixture(scope="module")
def ctx():
    m, f = synth()
    return R.Ctx(m, f)


def test_betas_recover_order(ctx):
    b = R.betas(ctx, date(2023, 3, 6), 60)
    assert len(b) == 8
    order = sorted(b, key=b.get)
    assert order[0] == R.ASSETS[0] and order[-1] == R.ASSETS[-1]


def test_prefix_invariance():
    m, f = synth(seed=2)
    D = date(2023, 3, 6)
    b1 = R.betas(R.Ctx(m, f), D, 60)
    m2 = {a: dict(bars) for a, bars in m.items()}
    for a in m2:
        for d in list(m2[a]):
            if d >= D - timedelta(days=1):
                o, h, l, c = m2[a][d]
                m2[a][d] = (o, h, l, c * 3)
    b2 = R.betas(R.Ctx(m2, f), D, 60)
    assert b1 == b2


def test_missing_day_makes_ineligible():
    D = date(2023, 3, 6)
    m, f = synth(seed=3, missing={("XRPUSDT", D - timedelta(days=10))})
    b = R.betas(R.Ctx(m, f), D, 60)
    assert "XRPUSDT" not in b and len(b) == 7


def test_select_beta_neutral_and_gross():
    beta = {a: 0.5 + 0.2 * i for i, a in enumerate(R.ASSETS)}
    pick = R.select(beta)
    L = sum(w for _, s, w, _ in pick if s > 0)
    S = sum(w for _, s, w, _ in pick if s < 0)
    assert abs(L + S - R.GROSS) < 1e-12
    bl = sum(b for _, s, _, b in pick if s > 0) / 3
    bs = sum(b for _, s, _, b in pick if s < 0) / 3
    assert abs(bl * L - bs * S) < 1e-12
    assert {a for a, s, _, _ in pick if s > 0} == set(R.ASSETS[:3])
    rev = R.select(beta, reverse=True)
    assert {a for a, s, _, _ in rev if s > 0} == set(R.ASSETS[-3:])
    assert R.select(dict(list(beta.items())[:5])) == []


def test_funding_edges_excluded(ctx):
    d0, d1 = date(2023, 3, 6), date(2023, 3, 13)
    leg = R.Leg(ctx, "BTCUSDT", -1, 0.1, 1.0, d0, d1, 10_000, 1)
    n_events = 7 * 3 - 1  # 00:00 vstupu ani 00:00 výstupu se nepočítá
    fund = leg.funding_until(R.day_ms(d1))
    avg_px = fund / (0.0001 * leg.qty * n_events)
    assert fund > 0  # short inkasuje kladnou sazbu
    assert 0.3 * leg.entry_fill < avg_px < 3 * leg.entry_fill


def test_cost_linearity(ctx):
    d0, d1 = date(2023, 3, 6), date(2023, 3, 13)
    nets = [R.Leg(ctx, "ETHUSDT", 1, 0.1, 1.0, d0, d1, 10_000, k).close()["costs"] for k in (1, 2, 3)]
    assert abs((nets[1] - nets[0]) - (nets[2] - nets[1])) < 1e-3 * abs(nets[0])  # téměř lineární (qty závisí na fill)
    assert nets[0] > 0


def test_short_liquidation():
    m, f = synth(seed=4)
    d0 = date(2023, 3, 6)
    a = "DOGEUSDT"
    o, h, l, c = m[a][d0 + timedelta(days=2)]
    m[a][d0 + timedelta(days=2)] = (o, m[a][d0][0] * 5, l, c)
    ctx = R.Ctx(m, f)
    leg = R.Leg(ctx, a, -1, 0.1, 1.0, d0, d0 + timedelta(days=7), 10_000, 1)
    r = leg.close()
    assert r["liquidated"] == 1
    assert abs(r["net_pnl"] - (-leg.notional - leg.fee_in + r["funding"])) < 1e-9
    assert leg.mtm(d0 + timedelta(days=5)) == pytest.approx(r["net_pnl"])


def test_simulate_ledger_matches_equity(ctx):
    rows, cv, dec = R.simulate(ctx, date(2023, 1, 1), date(2023, 6, 30), 60, 7, 2)
    assert rows and all(r["exit_day"] <= "2023-06-30" for r in rows)
    assert cv[date(2023, 6, 30)] - R.START_EQUITY == pytest.approx(sum(r["net_pnl"] for r in rows), abs=1e-6)
    assert len(rows) == 6 * sum(1 for x in dec if x["legs"])


def test_end_to_end_small(tmp_path, monkeypatch):
    m, f = synth(seed=5)
    monkeypatch.setattr(R, "PERIODS", {"tuning": ("2021-01-04", "2021-06-30"),
                                       "validation": ("2023-01-01", "2023-06-30"),
                                       "final_test": ("2025-01-01", "2025-06-30")})
    monkeypatch.setattr(R, "WF_YEARS", (2022,))
    res, ledger = R.evaluate(m, f)
    R.write(tmp_path, res, ledger, [], [])
    import csv
    sums = {}
    with (tmp_path / "trades.csv").open() as fh:
        for r in csv.DictReader(fh):
            k = f"{r['variant']}|{r['mode']}|{r['period']}|x{r['cost_multiplier']}"
            n, s = sums.get(k, (0, 0.0))
            sums[k] = (n + 1, s + float(r["net_pnl"]))
    for k, b in res["blocks"].items():
        n, s = sums.get(k, (0, 0.0))
        assert n == b["trades"] and s == pytest.approx(b["net_pnl"], abs=1e-6)
    assert res["verdict"]["status"] in ("ZAMÍTNUTO", "KANDIDÁT NA FORWARD PAPER")
