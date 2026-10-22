from dataclasses import replace
from datetime import datetime, timezone

from research.volatility_managed_momentum_v1 import (Config, DAY_MS, HOUR_MS, SYMBOLS,
                                                      allocation, backtest, daily_market)


def stamp(text):
    return int(datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp() * 1000)


def sample(gap=False):
    start = stamp("2022-01-01")
    market = {symbol: [] for symbol in SYMBOLS}
    gains = {"BTCUSDT": 0.001, "ETHUSDT": 0.0015, "SOLUSDT": 0.002, "XRPUSDT": -0.0005}
    prices = {symbol: 100.0 for symbol in SYMBOLS}
    for day in range(220):
        for hour in range(24):
            for symbol in SYMBOLS:
                opened = prices[symbol]
                prices[symbol] *= (1.0 + gains[symbol] / 24.0)
                if gap and symbol == "SOLUSDT" and day == 155 and hour == 3:
                    opened = prices[symbol] = 60.0
                market[symbol].append({"timestamp": start + day * DAY_MS + hour * HOUR_MS,
                                       "open": opened, "high": max(opened, prices[symbol]) * 1.001,
                                       "low": min(opened, prices[symbol]) * 0.999,
                                       "close": prices[symbol], "volume": 100.0})
    return market


def test_allocation_is_causal_and_uses_positive_assets():
    market = sample()
    daily = daily_market(market)
    weights = allocation(daily, 100)
    trimmed = {symbol: days[:101] for symbol, days in daily.items()}
    assert allocation(trimmed, 100) == weights
    assert "XRPUSDT" not in weights and weights
    assert sum(weights.values()) <= Config().gross_allocation


def test_entries_only_at_next_month_open_and_do_not_overlap_same_symbol():
    market = sample()
    result = backtest(market, stamp("2022-04-01"), stamp("2022-08-01"))
    assert result["trades"]
    for trade in result["trades"]:
        moment = datetime.fromtimestamp(trade["entry_ts"] / 1000, timezone.utc)
        assert moment.day == 1 and moment.hour == 0
    by_symbol = {}
    for trade in sorted(result["trades"], key=lambda item: item["entry_ts"]):
        previous = by_symbol.get(trade["symbol"])
        assert previous is None or previous <= trade["entry_ts"]
        by_symbol[trade["symbol"]] = trade["exit_ts"]


def test_gap_stop_and_higher_costs():
    market = sample(gap=True)
    base = backtest(market, stamp("2022-04-01"), stamp("2022-08-01"))
    assert any(trade["reason"] == "GAP_STOP" and trade["symbol"] == "SOLUSDT"
               for trade in base["trades"])
    costly = backtest(market, stamp("2022-04-01"), stamp("2022-08-01"),
                      replace(Config(), fee=0.0019, slippage=0.0004))
    assert costly["ending_equity"] < base["ending_equity"]


def test_misalignment_rejected():
    market = sample()
    market["ETHUSDT"].pop(3)
    try:
        backtest(market, stamp("2022-04-01"), stamp("2022-08-01"))
    except ValueError:
        pass
    else:
        raise AssertionError("misalignment was not rejected")


if __name__ == "__main__":
    tests = [value for name, value in list(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} tests passed")
