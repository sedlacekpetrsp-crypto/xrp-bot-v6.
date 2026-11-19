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
