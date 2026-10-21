from dataclasses import replace

from research.broad_shock_rebound_v1 import Config, HOUR_MS, SYMBOLS, backtest, signal


def sample(gap=False):
    market = {symbol: [] for symbol in SYMBOLS}
    for i in range(140):
        shock_step = max(0, min(6, i - 69))
        price = 100.0 * (0.99 ** shock_step)
        volume = 200.0 if 70 <= i <= 75 else 100.0
        for symbol in SYMBOLS:
            opened = 80.0 if gap and symbol == "SOLUSDT" and i == 77 else price
            market[symbol].append({"timestamp": i * HOUR_MS, "open": opened,
                                   "high": max(opened, price) * 1.001,
                                   "low": min(opened, price) * 0.999,
                                   "close": price, "volume": volume})
    return market


def test_signal_is_causal_and_entry_is_next_open():
    market = sample()
    setup = signal(market, 73)
    assert setup is not None
    trimmed = {symbol: bars[:74] for symbol, bars in market.items()}
    assert signal(trimmed, 73) == setup
    result = backtest(market, 60 * HOUR_MS, 130 * HOUR_MS)
    assert result["trades"][0]["entry_ts"] == 74 * HOUR_MS


def test_gap_stop_uses_worse_open():
    result = backtest(sample(gap=True), 60 * HOUR_MS, 130 * HOUR_MS)
    trade = result["trades"][0]
    assert trade["reason"] == "GAP_STOP"
    assert trade["exit"]["SOLUSDT"] < 80.0


def test_no_overlap_and_higher_costs_hurt():
    market = sample()
    base = backtest(market, 60 * HOUR_MS, 130 * HOUR_MS)
    costly = backtest(market, 60 * HOUR_MS, 130 * HOUR_MS,
                      replace(Config(), fee=0.0019, slippage=0.0004))
    assert costly["ending_equity"] < base["ending_equity"]
    trades = sorted(base["trades"], key=lambda trade: trade["entry_ts"])
    assert all(left["exit_ts"] <= right["entry_ts"] for left, right in zip(trades, trades[1:]))


def test_misalignment_rejected():
    market = sample()
    market["XRPUSDT"].pop(5)
    try:
        backtest(market, 60 * HOUR_MS, 130 * HOUR_MS)
    except ValueError:
        pass
    else:
        raise AssertionError("misalignment was not rejected")


if __name__ == "__main__":
    tests = [value for name, value in list(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} tests passed")
