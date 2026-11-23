"""A4 mechanika (syntetická data, ne důkaz výkonnosti)."""
import math
import random

from research.vortex_chop import run as R

STEP = 300_000


def mk(closes, t0=1_600_000_000_000, spread=0.5):
    bars, prev = [], closes[0]
    for i, c in enumerate(closes):
        o = prev
        bars.append((t0 + i * STEP, o, max(o, c) + spread, min(o, c) - spread, c))
        prev = c
    return bars


def test_uptrend_signals_up():
    bars = mk([100 + i for i in range(60)])
    s = R.signals(bars, 14, 50.0)
    assert s and all(v == 1 for v in s.values())


def test_downtrend_signals_down():
    bars = mk([200 - i for i in range(60)])
    s = R.signals(bars, 14, 50.0)
    assert s and all(v == -1 for v in s.values())


def test_chop_filters_sideways():
    bars = mk([100 + (1 if i % 2 else -1) for i in range(80)])
    assert R.signals(bars, 14, 38.2) == {}


def test_no_lookahead():
    random.seed(1)
    cl = [100.0]
    for _ in range(300):
        cl.append(cl[-1] * (1 + random.gauss(0, 0.004)))
    bars = mk(cl)
    full = R.signals(bars, 14, 50.0)
    for cut in (100, 200, 250):
        part = R.signals(bars[:cut + 1], 14, 50.0)
        assert all(full.get(i) == v for i, v in part.items())
        assert all(i in part for i in full if i <= cut)


def test_gap_blocks_window():
    bars = mk([100 + i for i in range(60)])
    bars = bars[:30] + [(t + STEP, o, h, l, c) for t, o, h, l, c in bars[30:]]
    s = R.signals(bars, 14, 50.0)
    assert not any(30 <= i < 44 for i in s)


def test_records_outcome_and_tie_is_up():
    bars = mk([100 + i for i in range(40)])
    t, o, h, l, c = bars[30]
    bars[30] = (t, o, h, l, o)  # close == open ⇒ UP
    recs = R.build_records(bars, {}, {29: 1, 28: -1})
    by = {r["t"]: r for r in recs}
    assert by[bars[30][0]]["up"] == 1 and by[bars[30][0]]["win"] == 1
    assert by[bars[29][0]]["win"] == 0


def test_wilson():
    assert abs(R.wilson_low(50, 100) - 0.4038) < 1e-3
    assert R.wilson_low(0, 0) == 0.0


def test_trackP_breakeven():
    recs = [{"t": 1_600_000_000_000 + i * STEP, "period": "tuning", "dir": 1, "win": int(i % 100 < 52), "up": 1,
             "prev_up": 1, "tiny": 0, "perp_ret": 0.0} for i in range(1000)]
    s = R.stats_period(recs)
    assert abs(s["hit_rate"] - 0.52) < 1e-12
    assert abs(s["trackP"]["x2"]["net_per_1usd_bets"]) < 1e-9
    assert s["trackP"]["x1"]["net_per_1usd_bets"] > 0 > s["trackP"]["x3"]["net_per_1usd_bets"]
    assert abs(s["trackF"]["x1"]["net"] + 1000 * R.NOTIONAL * R.PERP_COST) < 1e-6


def test_period_bounds():
    ms = lambda d: int(__import__("datetime").datetime.fromisoformat(d + "T00:00:00+00:00").timestamp() * 1000)
    assert R.period_of(ms("2022-12-31")) == "tuning"
    assert R.period_of(ms("2023-01-01")) == "validation"
    assert R.period_of(ms("2025-01-01")) == "final_test"
    assert R.period_of(ms("2026-11-01")) is None
