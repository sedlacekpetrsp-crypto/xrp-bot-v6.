"""Syntetické testy mechaniky vol-target (nejsou důkazem ziskovosti)."""
import math
import random
from datetime import date, datetime, timezone

from research.vol_target import run as vt


def bars_from_closes(closes, start=date(2020, 1, 1)):
    out, prev = [], closes[0]
    for i, c in enumerate(closes):
        ts = int(datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp() * 1000) + i * 86_400_000
        out.append({"ts": ts, "open": prev, "high": max(prev, c), "low": min(prev, c), "close": c})
        prev = c
    return out


def random_walk(n, vol, seed=1):
    rnd = random.Random(seed)
    p, xs = 100.0, []
    for _ in range(n):
        p *= math.exp(rnd.gauss(0, vol))
        xs.append(p)
    return xs


def test_sigma_matches_manual():
    closes = random_walk(40, 0.03)
    s = vt.sigma_series(bars_from_closes(closes))
    d = sorted(s)[-1]
    r = [math.log(closes[i] / closes[i - 1]) for i in range(len(closes) - 30, len(closes))]
    mu = sum(r) / 30
    manual = math.sqrt(sum((x - mu) ** 2 for x in r) / 29) * math.sqrt(365)
    assert abs(s[d] - manual) < 1e-12


def test_ledger_sum_equals_pnl_and_continuous():
    bars = bars_from_closes(random_walk(400, 0.04, seed=7))
    for mult in (1, 2, 3):
        rows, cv = vt.simulate(bars, date(2020, 3, 1), date(2021, 1, 31), mult)
        assert abs(sum(r["net_pnl"] for r in rows) - (cv[max(cv)] - vt.START_EQUITY)) < 1e-6
        for a, b in zip(rows, rows[1:]):
            assert a["exit_day"] == b["entry_day"] and abs(a["end_value"] - b["start_value"]) < 1e-9
        assert len(rows) > 1  # 4 % denní vol ≈ 76 % p.a. ⇒ w ≈ 0,5 a úpravy


def test_low_vol_equals_buy_hold():
    # σ << 40 % ⇒ w* = 1 ⇒ jediný úsek, shodné s B&H
    bars = bars_from_closes(random_walk(300, 0.005, seed=3))
    s, e = date(2020, 3, 1), date(2020, 9, 30)
    rows, cv = vt.simulate(bars, s, e, 2)
    bh = vt.buy_hold(bars, s, e, 2)
    assert len(rows) == 1
    assert abs(cv[e] - bh[e]) < 1e-6


def test_missing_day_raises():
    bars = bars_from_closes(random_walk(100, 0.02))
    del bars[60]
    try:
        vt.simulate(bars, date(2020, 2, 15), date(2020, 4, 1), 1)
    except ValueError:
        return
    raise AssertionError("chybějící den musí skončit chybou")


def test_band_respected():
    bars = bars_from_closes(random_walk(400, 0.04, seed=11))
    rows, _ = vt.simulate(bars, date(2020, 3, 1), date(2021, 1, 31), 1)
    for r in rows[1:]:
        assert abs(r["w_to"] - r["w_from"]) > vt.BAND - 1e-9
        assert r["w_to"] <= 1.0
