import unittest
from dataclasses import replace
from datetime import datetime, timezone

from research.weekend_carry_v1 import Config, HOUR_MS, SYMBOLS, backtest, is_entry_time


def stamp(text):
    return int(datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp() * 1000)


def sample(hours=80, gap_symbol=None, gap_hour=None):
    start = stamp("2026-01-03T00:00:00")  # Saturday
    market = {symbol: [] for symbol in SYMBOLS}
    for i in range(hours):
        price = 100.0 + i * 0.01
        for symbol in SYMBOLS:
            opened = 80.0 if symbol == gap_symbol and i == gap_hour else price
            market[symbol].append({"timestamp": start + i * HOUR_MS, "open": opened,
                                   "high": max(opened, price) * 1.001,
                                   "low": min(opened, price) * 0.999,
                                   "close": price, "volume": 1.0})
    return market


class WeekendCarryTests(unittest.TestCase):
    def config(self, **kwargs):
        return replace(Config(), fee=0.0, slippage=0.0, **kwargs)

    def test_calendar_entry_and_fixed_exit_are_causal(self):
        market = sample()
        start = market[SYMBOLS[0]][0]["timestamp"]
        result = backtest(market, start, start + 80 * HOUR_MS, self.config())
        self.assertEqual({trade["entry_ts"] for trade in result["trades"]}, {start})
        self.assertTrue(all(trade["exit_ts"] == start + 48 * HOUR_MS
                            for trade in result["trades"]))
        self.assertTrue(is_entry_time(start))

    def test_four_legs_do_not_overlap(self):
        market = sample(hours=250)
        start = market[SYMBOLS[0]][0]["timestamp"]
        result = backtest(market, start, start + 250 * HOUR_MS, self.config())
        entries = [trade["entry_ts"] for trade in result["trades"]]
        self.assertEqual(len(set(entries)), 2)
        self.assertEqual(len(entries), 8)

    def test_gap_stop_fills_at_worse_open(self):
        market = sample(gap_symbol="SOLUSDT", gap_hour=10)
        start = market[SYMBOLS[0]][0]["timestamp"]
        result = backtest(market, start, start + 80 * HOUR_MS, self.config())
        trade = next(trade for trade in result["trades"] if trade["symbol"] == "SOLUSDT")
        self.assertEqual(trade["reason"], "GAP_STOP")
        self.assertEqual(trade["exit"], 80.0)

    def test_higher_costs_reduce_equity(self):
        market = sample()
        start = market[SYMBOLS[0]][0]["timestamp"]
        low = backtest(market, start, start + 80 * HOUR_MS, Config(fee=0.0001, slippage=0.0001))
        high = backtest(market, start, start + 80 * HOUR_MS, Config(fee=0.001, slippage=0.001))
        self.assertLess(high["ending_equity"], low["ending_equity"])

    def test_timestamp_misalignment_is_rejected(self):
        market = sample()
        market["XRPUSDT"][2]["timestamp"] += HOUR_MS
        with self.assertRaises(ValueError):
            backtest(market, 0, 10**15)


if __name__ == "__main__":
    unittest.main()
