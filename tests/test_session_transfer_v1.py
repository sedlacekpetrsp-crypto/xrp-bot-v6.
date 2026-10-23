import unittest
from dataclasses import replace

from research.session_transfer_v1 import Config, HOUR_MS, backtest, signal


def bars(prices, opens=None, highs=None, lows=None):
    opens = opens or prices
    highs = highs or [max(o, c) for o, c in zip(opens, prices)]
    lows = lows or [min(o, c) for o, c in zip(opens, prices)]
    return [{"timestamp": i * HOUR_MS, "open": o, "high": h, "low": l,
             "close": c, "volume": 1.0}
            for i, (o, h, l, c) in enumerate(zip(opens, highs, lows, prices))]


class SessionTransferTests(unittest.TestCase):
    def config(self, **kwargs):
        base = Config(threshold=0.005, fee=0.0, slippage=0.0, annual_borrow=0.0)
        return replace(base, **kwargs)

    def test_completed_session_enters_at_08_open_and_exits_at_16(self):
        prices = [100 + i * 0.2 for i in range(20)]
        data = bars(prices)
        result = backtest(data, 0, 20 * HOUR_MS, self.config(stop=0.20, target=0.20))
        trade = result["trades"][0]
        self.assertEqual(signal(data, 8, self.config()), "LONG")
        self.assertEqual(trade["entry_ts"], 8 * HOUR_MS)
        self.assertEqual(trade["exit_ts"], 16 * HOUR_MS)
        self.assertEqual(trade["reason"], "TIME")

    def test_signal_rejects_data_gap(self):
        data = bars([100 + i * 0.2 for i in range(12)])
        data[4]["timestamp"] += 24 * HOUR_MS
        self.assertIsNone(signal(data, 8, self.config()))

    def test_short_gap_stop_uses_worse_open(self):
        prices = [100 - i * 0.2 for i in range(20)]
        opens = list(prices)
        opens[10] = 110.0
        data = bars(prices, opens)
        result = backtest(data, 0, 20 * HOUR_MS, self.config(stop=0.025, target=0.20))
        trade = result["trades"][0]
        self.assertEqual(trade["side"], "SHORT")
        self.assertEqual(trade["reason"], "GAP_STOP")
        self.assertEqual(trade["exit"], 110.0)

    def test_stop_wins_same_bar_ambiguity(self):
        prices = [100 + i * 0.2 for i in range(12)]
        data = bars(prices)
        data[8]["high"] = 110.0
        data[8]["low"] = 90.0
        result = backtest(data, 0, 12 * HOUR_MS, self.config(stop=0.02, target=0.02))
        self.assertEqual(result["trades"][0]["reason"], "STOP")

    def test_short_borrow_and_higher_costs_reduce_equity(self):
        data = bars([100 - i * 0.2 for i in range(20)])
        low = backtest(data, 0, 20 * HOUR_MS,
                       self.config(fee=0.0001, slippage=0.0001, annual_borrow=0.04,
                                   stop=0.20, target=0.20))
        high = backtest(data, 0, 20 * HOUR_MS,
                        self.config(fee=0.001, slippage=0.001, annual_borrow=0.16,
                                    stop=0.20, target=0.20))
        self.assertGreater(low["trades"][0]["borrow_cost"], 0)
        self.assertLess(high["ending_equity"], low["ending_equity"])


if __name__ == "__main__":
    unittest.main()
