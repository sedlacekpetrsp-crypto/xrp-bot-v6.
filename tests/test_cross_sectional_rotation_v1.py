from dataclasses import replace

from research.cross_sectional_rotation_v1 import Config, DAY_MS, backtest, desired_symbol


def market(days=100, gap=False):
    output = {}
    for symbol, daily_gain in (("BTCUSDT", 0.002), ("ETHUSDT", 0.004), ("SOLUSDT", 0.006), ("XRPUSDT", 0.003)):
        bars = []
        price = 100.0
        for day in range(days):
            for slot in range(96):
                opened = price
                price *= (1.0 + daily_gain / 96.0)
                low = min(opened, price) * 0.999
                if gap and symbol == "SOLUSDT" and day == 65 and slot == 1:
                    opened = price = 70.0
                    low = 69.0
                bars.append({"timestamp": day * DAY_MS + slot * 900_000, "open": opened,
                             "high": max(opened, price) * 1.001, "low": low,
                             "close": price, "volume": 100.0})
        output[symbol] = bars
    return output


def daily_view(data):
    result = {}
    for symbol, bars in data.items():
        result[symbol] = [{"timestamp": d * DAY_MS, "open": bars[d * 96]["open"],
                           "high": max(x["high"] for x in bars[d * 96:(d + 1) * 96]),
                           "low": min(x["low"] for x in bars[d * 96:(d + 1) * 96]),
                           "close": bars[(d + 1) * 96 - 1]["close"]}
                          for d in range(len(bars) // 96)]
    return result


def test_signal_is_causal_and_selects_relative_winner():
    data = market()
    daily = daily_view(data)
    assert desired_symbol(daily, 64) == "SOLUSDT"
    trimmed = {s: rows[:65] for s, rows in daily.items()}
    assert desired_symbol(trimmed, 64) == "SOLUSDT"


def test_entry_is_next_day_open_and_only_one_position_overlaps():
    data = market()
    result = backtest(data, 61 * DAY_MS, 90 * DAY_MS)
    assert result["trades"]
    assert result["trades"][0]["entry_ts"] == 61 * DAY_MS
    ordered = sorted(result["trades"], key=lambda x: x["entry_ts"])
    assert all(a["exit_ts"] <= b["entry_ts"] for a, b in zip(ordered, ordered[1:]))


def test_gap_stop_uses_worse_open():
    result = backtest(market(gap=True), 61 * DAY_MS, 90 * DAY_MS,
                      replace(Config(), stop_atr=0.5))
    stopped = next(x for x in result["trades"] if x["reason"] == "GAP_STOP")
    assert stopped["exit"] < 70.0


def test_higher_costs_reduce_equity():
    data = market()
    base = backtest(data, 61 * DAY_MS, 90 * DAY_MS)
    costly = backtest(data, 61 * DAY_MS, 90 * DAY_MS,
                      replace(Config(), fee=0.0019, slippage=0.0004))
    assert costly["ending_equity"] < base["ending_equity"]


def test_alignment_gap_is_rejected():
    data = market()
    data["ETHUSDT"].pop(10)
    try:
        backtest(data, 61 * DAY_MS, 90 * DAY_MS)
    except ValueError:
        pass
    else:
        raise AssertionError("gap was not rejected")


if __name__ == "__main__":
    tests = [value for name, value in list(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} tests passed")
