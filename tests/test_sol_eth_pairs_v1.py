from dataclasses import replace

from research.sol_eth_pairs_v1 import Config, HOUR_MS, backtest, ratio_series, zscore


def sample(gap=False):
    market = {"SOLUSDT": [], "ETHUSDT": []}
    for i in range(900):
        eth = 100.0
        sol = 100.0 if i < 730 or i >= 750 else 150.0
        if gap and i == 732:
            sol = 200.0
        for symbol, price in (("SOLUSDT", sol), ("ETHUSDT", eth)):
            market[symbol].append({"timestamp": i * HOUR_MS, "open": price,
                                   "high": price * 1.001, "low": price * 0.999,
                                   "close": price, "volume": 100.0})
    return market


def test_zscore_is_causal_and_entry_is_next_open():
    market = sample()
    ratios = ratio_series(market)
    value = zscore(ratios, 730)
    assert value == zscore(ratios[:731], 730)
    result = backtest(market, 720 * HOUR_MS, 850 * HOUR_MS)
    assert result["trades"]
    assert result["trades"][0]["entry_ts"] == 731 * HOUR_MS
    assert result["trades"][0]["side_sol"] == -1


def test_gap_stop_uses_worse_open():
    result = backtest(sample(gap=True), 720 * HOUR_MS, 850 * HOUR_MS)
    trade = result["trades"][0]
    assert trade["reason"] == "GAP_STOP"
    assert trade["exit"]["SOLUSDT"] > 200.0


def test_one_pair_at_a_time_and_costs_hurt():
    market = sample()
    base = backtest(market, 720 * HOUR_MS, 850 * HOUR_MS)
    costly = backtest(market, 720 * HOUR_MS, 850 * HOUR_MS,
                      replace(Config(), fee=0.0019, slippage=0.0004,
                              short_borrow_annual=0.16))
    assert costly["ending_equity"] < base["ending_equity"]
    trades = sorted(base["trades"], key=lambda trade: trade["entry_ts"])
    assert all(left["exit_ts"] <= right["entry_ts"] for left, right in zip(trades, trades[1:]))


def test_timestamp_misalignment_is_rejected():
    market = sample()
    market["ETHUSDT"].pop(4)
    try:
        backtest(market, 720 * HOUR_MS, 850 * HOUR_MS)
    except ValueError:
        pass
    else:
        raise AssertionError("misalignment was not rejected")


if __name__ == "__main__":
    tests = [value for name, value in list(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} tests passed")
