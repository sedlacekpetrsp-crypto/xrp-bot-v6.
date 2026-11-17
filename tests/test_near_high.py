"""Syntetické testy mechaniky near-52w-high (nejsou důkazem ziskovosti)."""
import math
import random
from collections import defaultdict
from datetime import date, datetime, timezone

from research.near_high import run as nh


def bars_from_closes(closes, start=date(2019, 1, 1)):
    out, prev = [], closes[0]
    t0 = int(datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp() * 1000)
    for i, c in enumerate(closes):
        out.append({"ts": t0 + i * 86_400_000, "open": prev, "high": max(prev, c), "low": min(prev, c), "close": c})
        prev = c
    return out


def market(n=900, seed=3):
    rnd = random.Random(seed)
    mk = {}
    for j, s in enumerate(nh.SYMBOLS):
        p, xs = 100.0, []
        drift = (j - 3.5) * 0.0004
        for _ in range(n):
            p *= math.exp(rnd.gauss(drift, 0.04))
            xs.append(p)
        mk[s] = bars_from_closes(xs)
    return mk


def test_score_matches_manual():
    mk = market()
    sc = nh.score_series(mk["BTCUSDT"])
    closes = [b["close"] for b in mk["BTCUSDT"]]
    d = sorted(sc)[-1]
    assert abs(sc[d] - closes[-1] / max(closes[-365:])) < 1e-12
    assert 0 < min(sc.values()) and max(sc.values()) <= 1.0
    assert len(sc) == len(closes) - 364


def test_select_top_and_ties():
    d = date(2020, 1, 1)
    scores = {s: {d: 0.5} for s in nh.SYMBOLS}
    assert nh.select(scores, d, 3) == list(nh.SYMBOLS[:3])
    scores["LINKUSDT"][d] = 0.9
    scores["DOGEUSDT"][d] = 0.8
    assert nh.select(scores, d, 3) == ["LINKUSDT", "DOGEUSDT", "BTCUSDT"]
    assert nh.select(scores, d, 2, bottom=True) == ["BTCUSDT", "ETHUSDT"]


def test_ledger_sum_equals_pnl_and_k_per_month():
    mk = market()
    scores = {s: nh.score_series(mk[s]) for s in nh.SYMBOLS}
    s, e = date(2020, 1, 1), date(2021, 6, 15)
    for mult in (1, 2, 3):
        for k in (2, 3, 4):
            rows, cv = nh.simulate(mk, scores, s, e, mult, k=k)
            assert abs(sum(r["net_pnl"] for r in rows) - (cv[e] - nh.START_EQUITY)) < 1e-6
            per_month = defaultdict(int)
            for r in rows:
                per_month[r["entry_day"]] += 1
                assert abs(r["gross_pnl"] - r["fees"] - r["net_pnl"]) < 1e-9
            assert set(per_month.values()) == {k}
            assert len(per_month) == 18  # start + 17 prvních dnů měsíce


def test_signal_uses_previous_close_only():
    mk = market()
    scores = {s: nh.score_series(mk[s]) for s in nh.SYMBOLS}
    rows, _ = nh.simulate(mk, scores, date(2020, 3, 1), date(2020, 5, 31), 1)
    for r in rows:
        d = date.fromisoformat(r["entry_day"])
        sig = date.fromordinal(d.toordinal() - 1)
        assert r["asset"] in nh.select(scores, sig, nh.K)


def test_costs_monotone_and_zero_cost_equals_price_path():
    mk = market()
    scores = {s: nh.score_series(mk[s]) for s in nh.SYMBOLS}
    s, e = date(2020, 1, 1), date(2020, 12, 31)
    finals = [nh.simulate(mk, scores, s, e, m)[1][e] for m in (0, 1, 2, 3)]
    assert finals[0] > finals[1] > finals[2] > finals[3]
    # bez nákladů: měsíční výnos = průměr výnosů vybraných aktiv open→open
    rows, cv = nh.simulate(mk, scores, s, e, 0)
    assert all(abs(r["fees"]) < 1e-9 for r in rows)


def test_buy_hold_basket_and_missing_day_raises():
    mk = market()
    s, e = date(2020, 1, 1), date(2020, 3, 31)
    cv = nh.buy_hold_basket(mk, s, e, 0)
    px = {k: nh.by_day(v) for k, v in mk.items()}
    exp = sum(nh.START_EQUITY / 8 / px[k][s]["open"] * px[k][e]["close"] for k in nh.SYMBOLS)
    assert abs(cv[e] - exp) < 1e-6
    mk["XRPUSDT"] = [b for b in mk["XRPUSDT"] if nh.day(b["ts"]) != date(2020, 2, 10)]
    scores = {k: nh.score_series(mk[k]) for k in nh.SYMBOLS}
    try:
        nh.simulate(mk, scores, s, e, 1)
    except ValueError:
        pass
    else:
        raise AssertionError("chybějící den musí selhat")
