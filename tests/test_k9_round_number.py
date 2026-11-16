"""Syntetické testy K9 fáze A (žádná tržní data, žádné výnosy)."""
import numpy as np
import pandas as pd

from research.k9_round_number.events import (block_bootstrap_diff, detect_touches, level_above,
                                             level_below)


def _frame(highs, lows, vol=None, buy=None):
    n = len(highs)
    idx = pd.date_range("2021-01-01", periods=n, freq="1min")
    vol = np.full(n, 10.0) if vol is None else np.asarray(vol, float)
    buy = vol / 2 if buy is None else np.asarray(buy, float)
    close = (np.asarray(highs) + np.asarray(lows)) / 2
    return pd.DataFrame({"high": highs, "low": lows, "close": close, "volume": vol, "taker_buy": buy}, index=idx)


def test_levels_strict_and_float_safe():
    assert level_above(1000.0, 1000.0, 0.0) == 2000.0
    assert level_below(1000.0, 1000.0, 0.0) == 0.0
    assert level_above(0.3, 0.1, 0.0) == 0.4  # bez chyby float 0.30000000000000004
    assert level_above(0.29, 0.1, 0.0) == 0.3
    assert level_above(1370.0, 1000.0, 0.37) == 2370.0
    assert level_below(1370.0, 1000.0, 0.37) == 370.0


def test_first_touch_up_with_volume_and_direction():
    highs = [990.0] * 61 + [1001.0]
    lows = [980.0] * 62
    vol = [10.0] * 61 + [30.0]
    buy = [5.0] * 61 + [24.0]
    ev = detect_touches(_frame(highs, lows, vol, buy), 1000.0, 0.0)
    assert len(ev) == 1
    e = ev.iloc[0]
    assert e.level == 1000.0 and e.direction == 1
    assert np.isclose(e.r_vol, np.log(3.0)) and np.isclose(e.m2, 0.8 - 0.5)


def test_no_event_when_touched_within_lookback():
    highs = [990.0] * 30 + [1000.5] + [990.0] * 30 + [1001.0]
    ev = detect_touches(_frame(highs, [980.0] * 62), 1000.0, 0.0)
    assert ev.empty  # dotyk v t-31 ⇒ ne první dotyk po 60 min


def test_down_touch_direction_uses_sell_share():
    highs = [1020.0] * 62
    lows = [1010.0] * 61 + [999.0]
    buy = [5.0] * 61 + [2.0]
    ev = detect_touches(_frame(highs, lows, buy=buy), 1000.0, 0.0)
    assert len(ev) == 1 and ev.iloc[0].direction == -1
    assert np.isclose(ev.iloc[0].m2, 0.8 - 0.5)


def test_insufficient_history_no_event():
    ev = detect_touches(_frame([990.0] * 30 + [1001.0], [980.0] * 31), 1000.0, 0.0)
    assert ev.empty


def test_bootstrap_detects_shift_and_null():
    rng = np.random.default_rng(1)
    t = pd.date_range("2021-01-01", periods=400, freq="6h")
    a = pd.DataFrame({"time": t, "r_vol": rng.normal(0.3, 0.2, 400)})
    b = pd.DataFrame({"time": t, "r_vol": rng.normal(0.0, 0.2, 400)})
    p, lo, hi = block_bootstrap_diff(a, b, "r_vol", reps=2000)
    assert lo > 0.2 and hi < 0.4 and lo < p < hi
    c = pd.DataFrame({"time": t, "r_vol": rng.normal(0.0, 0.2, 400)})
    _, lo0, hi0 = block_bootstrap_diff(c, b, "r_vol", reps=2000)
    assert lo0 < 0 < hi0
