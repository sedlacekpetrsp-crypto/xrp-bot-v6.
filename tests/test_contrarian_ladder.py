"""Syntetické testy mechaniky kontrariánského žebříku (nejsou důkazem ziskovosti)."""
import math
import random
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from research.contrarian_ladder import run as cl


def bars_from_closes(closes, start=date(2019, 1, 1)):
    out, prev = [], closes[0]
    t0 = int(datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp() * 1000)
    for i, c in enumerate(closes):
        out.append({"ts": t0 + i * 86_400_000, "open": prev, "high": max(prev, c), "low": min(prev, c), "close": c})
        prev = c
    return out


def market(n=1100, seed=5):
    rnd = random.Random(seed)
    mk = {}
    for j, s in enumerate(cl.SYMBOLS):
        p, xs = 100.0, []
        for _ in range(n):
            p *= math.exp(rnd.gauss((j - 3.5) * 0.0003, 0.045))
            xs.append(p)
        mk[s] = bars_from_closes(xs)
    return mk


def test_drawdown_matches_manual():
    mk = market()
    dd = cl.drawdown_series(mk["BTCUSDT"])
    closes = [b["close"] for b in mk["BTCUSDT"]]
    assert abs(dd[sorted(dd)[-1]] - (1 - closes[-1] / max(closes[-365:]))) < 1e-12
    assert min(dd.values()) >= 0.0 and max(dd.values()) < 1
    assert len(dd) == len(closes) - 364


def scripted(closes_after, pre=365, start=date(2019, 1, 1)):
    """Rovných `pre` dní na 100, pak zadané close; vrací (bars_by_day, dd, první den simulace)."""
    bars = bars_from_closes([100.0] * pre + closes_after, start)
    return cl.by_day(bars), cl.drawdown_series(bars), start + timedelta(days=pre)


def test_tranches_reset_and_timing():
    # den0 100, den1 79 (DD 21 % ⇒ 1 tranše za open dne2 = 79), den2 65 (DD 35 % ⇒ 2. tranše za open dne3 = 65),
    # den3 59 (DD 41 % ⇒ 3. za open dne4 = 59), den4 101 (nové max ⇒ reset za open dne5 = 101), den5 101
    bd, dd, s = scripted([100, 79, 65, 59, 101, 101])
    rows, cv = cl.simulate_sleeve(bd, dd, s, s + timedelta(days=5), 0, 1000.0)
    tr = [r for r in rows if r["kind"] == "TRANCHE"]
    assert [r["entry_day"] for r in tr] == [(s + timedelta(days=k)).isoformat() for k in (2, 3, 4)]
    assert all(r["exit_day"] == (s + timedelta(days=5)).isoformat() for r in tr)
    assert [r["level"] for r in tr] == [0.20, 0.30, 0.40]
    # bez nákladů: tranše 500/3, 500/3, zbytek; výstup za 101
    exp = [500 / 3 * 101 / 79, 500 / 3 * 101 / 65, 500 / 3 * 101 / 59]
    assert all(abs(r["end_value"] - e) < 1e-9 for r, e in zip(tr, exp))
    assert abs(sum(r["start_value"] for r in tr) - 500) < 1e-9
    total = sum(r["net_pnl"] for r in rows)
    assert abs(total - (cv[max(cv)] - 1000)) < 1e-9


def test_gap_buys_multiple_levels_same_day_and_no_ladder():
    bd, dd, s = scripted([100, 55, 55, 55])
    rows, _ = cl.simulate_sleeve(bd, dd, s, s + timedelta(days=3), 1, 1000.0)
    tr = [r for r in rows if r["kind"] == "TRANCHE"]
    assert len(tr) == 3 and len({r["entry_day"] for r in tr}) == 1
    rows0, cv0 = cl.simulate_sleeve(bd, dd, s, s + timedelta(days=3), 1, 1000.0, ladder=False)
    assert [r["kind"] for r in rows0] == ["BASE"]
    assert abs(rows0[0]["net_pnl"] - (cv0[max(cv0)] - 1000)) < 1e-9


def test_signal_uses_only_past_close():
    """Změna close v den t+1 nesmí změnit rozhodnutí z close dne t (vstup za open t+1)."""
    a, dda, s = scripted([100, 79, 80, 80])
    b, ddb, _ = scripted([100, 79, 120, 80])
    ra, _ = cl.simulate_sleeve(a, dda, s, s + timedelta(days=3), 1, 1000.0)
    rb, _ = cl.simulate_sleeve(b, ddb, s, s + timedelta(days=3), 1, 1000.0)
    ea = [r["entry_day"] for r in ra if r["kind"] == "TRANCHE"]
    eb = [r["entry_day"] for r in rb if r["kind"] == "TRANCHE"]
    assert ea == eb == [(s + timedelta(days=2)).isoformat()]


def test_ledger_sum_equals_pnl_and_costs_monotone():
    mk = market()
    dds = {s: cl.drawdown_series(mk[s]) for s in cl.SYMBOLS}
    s, e = date(2020, 1, 15), date(2021, 12, 31)
    nets = []
    for mult in (1, 2, 3):
        for lv in (cl.LEVELS, *cl.NEIGHBORS.values()):
            rows, cv = cl.simulate(mk, dds, s, e, mult, levels=lv)
            assert abs(sum(r["net_pnl"] for r in rows) - (cv[e] - cl.START_EQUITY)) < 1e-6
            per = defaultdict(int)
            for r in rows:
                if r["kind"] == "BASE":
                    per[r["asset"]] += 1
            assert set(per.values()) == {1} and len(per) == 8
        nets.append(cl.simulate(mk, dds, s, e, mult)[1][e])
    assert nets[0] > nets[1] > nets[2]


def test_evaluate_end_to_end_synthetic(monkeypatch):
    mk = market(n=2700)  # 2019-01-01 … ~2026-05
    monkeypatch.setattr(cl, "PERIODS", {"tuning": ("2020-09-01", "2022-12-31"),
                                         "validation": ("2023-01-01", "2024-12-31"),
                                         "final_test": ("2025-01-01", "2026-04-30")})
    res, ledger = cl.evaluate(mk)
    blocks = defaultdict(lambda: [0, 0.0])
    for r in ledger:
        k = (r["variant"], r["period"], r["cost_multiplier"])
        blocks[k][0] += r["kind"] == "TRANCHE"
        blocks[k][1] += r["net_pnl"]
    for p in cl.PERIODS:
        for m in cl.COST_MULTIPLIERS:
            g = res["strategy"][f"{p}/x{m}"]
            assert blocks[("L20_30_40", p, m)][0] == g["trades"]
            assert abs(blocks[("L20_30_40", p, m)][1] - g["net_pnl"]) < 1e-6
    assert res["verdict"]["status"] in ("ZAMÍTNUTO", "KANDIDÁT NA FORWARD PAPER")
    assert "dsr" in res["dsr_validation_x1"]
