"""K9 execution-price validity: synthetic-only regression, no historical performance."""
import numpy as np
import pandas as pd
import pytest

from research.k9_round_number.phase_b import build_trades


def _fixture(entry=100.0, exit_price=101.0):
    idx = pd.date_range("2023-06-01", periods=90, freq="min", tz="UTC")
    grid = pd.DataFrame({"open": 100.0, "close": 100.0}, index=idx)
    grid.loc[idx[11], "open"] = entry
    grid.loc[idx[25], "close"] = exit_price
    events = pd.DataFrame({"time": [idx[10]], "level": [100.0], "direction": [1]})
    return grid, events


@pytest.mark.parametrize("entry,exit_price", [
    (0.0, 101.0), (-1.0, 101.0), (np.inf, 101.0),
    (np.nan, 101.0), (100.0, 0.0), (100.0, -2.0),
    (100.0, np.inf), (100.0, -np.inf),
])
def test_invalid_execution_price_rejects_trade(entry, exit_price):
    grid, events = _fixture(entry, exit_price)
    trades, stats = build_trades(grid, events, 15, "XRPUSDT", "round")
    assert trades.empty
    assert len(stats["invalid"]) == 1
    assert len(stats["taken"]) == 1


def test_valid_execution_prices_preserved():
    grid, events = _fixture()
    trades, stats = build_trades(grid, events, 15, "XRPUSDT", "round")
    assert len(trades) == 1
    assert not stats["invalid"]
    assert np.isfinite(trades.iloc[0]["gross"])


@pytest.mark.parametrize("bad", [0.0, -1.0, np.inf])
def test_random_benchmark_rejects_invalid_execution_price(bad):
    """Review Claude 2026-11-19: stejná maska musí platit i pro benchmark d) (random_trades), ne jen build_trades.
    Minuta s neplatnou cenou uvnitř okna 13:30–13:45 vyřadí kandidáty, jejichž okno [i+1, i+H] ji obsahuje."""
    from research.k9_round_number import phase_b

    idx = pd.date_range("2024-02-01 00:00", periods=3000, freq="min", tz="UTC")
    c = 100 + 0.01 * np.arange(len(idx))
    g = pd.DataFrame({"open": np.concatenate([[100.0], c[:-1]]), "close": c, "volume": 10.0}, index=idx)
    src = pd.DataFrame({"asset": ["XRPUSDT"], "time": [pd.Timestamp("2024-02-01 13:05", tz="UTC")], "direction": [1]})
    base = phase_b.random_trades(g, src, 15, np.random.default_rng(0), n=59)
    bad_t = pd.Timestamp("2024-02-01 13:40", tz="UTC")
    g.loc[bad_t, "close"] = bad
    r = phase_b.random_trades(g, src, 15, np.random.default_rng(0), n=59)
    hit = lambda t: (t + pd.Timedelta(minutes=1) <= bad_t) & (bad_t <= t + pd.Timedelta(minutes=15))
    assert hit(base["time"]).any()            # bez masky by kontaminované okno bylo vybráno
    assert not hit(r["time"]).any()
    assert np.isfinite(r["gross"]).all()
