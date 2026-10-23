import unittest
from dataclasses import replace
from math import exp

from research.volatility_contraction_spot_v1 import Config, HOUR_MS, backtest, signal, volatility_ratio


def sample():
    config = Config(short_hours=4, long_hours=12, contraction_ratio=0.35,
                    hold_hours=4, cooldown_hours=4, stop=0.20,
                    fee=0.0, slippage=0.0)
    returns = [0.04, -0.04] * 6 + [0.0005] * 16
    price = 100.0
    bars = [{"timestamp": 0, "open": price, "high": price, "low": price,
             "close": price, "volume": 1.0}]
    for i, value in enumerate(returns, 1):
        opened = price
        price *= exp(value)
        bars.append({"timestamp": i * HOUR_MS, "open": opened,
                     "high": max(opened, price), "low": min(opened, price),
                     "close": price, "volume": 1.0})
    return bars, config


class VolatilityContractionTests(unittest.TestCase):
    def test_crossing_signal_is_causal_and_enters_next_open(self):
        bars, config = sample()
        entries = [i for i in range(len(bars)) if signal(bars, i, config)]
        self.assertTrue(entries)
        i = entries[0]
        result = backtest(bars, 0, len(bars) * HOUR_MS, config)
        self.assertEqual(result["trades"][0]["entry_ts"], bars[i]["timestamp"])
        self.assertEqual(signal(bars[:i + 1], i, config), signal(bars, i, config))

    def test_ratio_rejects_gap(self):
        bars, config = sample()
        bars[5]["timestamp"] += 24 * HOUR_MS
        self.assertIsNone(volatility_ratio(bars, 12, config))

    def test_time_exit_and_no_overlap(self):
        bars, config = sample()
        result = backtest(bars, 0, len(bars) * HOUR_MS, config)
        self.assertTrue(result["trades"])
        self.assertTrue(all(trade["exit_ts"] - trade["entry_ts"] <= config.hold_hours * HOUR_MS
                            for trade in result["trades"]))
        for first, second in zip(result["trades"], result["trades"][1:]):
            self.assertGreaterEqual(second["entry_ts"], first["exit_ts"] + config.cooldown_hours * HOUR_MS)

    def test_gap_stop_uses_worse_open(self):
        bars, config = sample()
        entry = next(i for i in range(len(bars)) if signal(bars, i, config))
        bars[entry + 1]["open"] = bars[entry]["open"] * 0.70
        bars[entry + 1]["low"] = min(bars[entry + 1]["low"], bars[entry + 1]["open"])
        bars[entry + 1]["high"] = max(bars[entry + 1]["high"], bars[entry + 1]["open"])
        result = backtest(bars, 0, len(bars) * HOUR_MS, replace(config, stop=0.08))
        self.assertEqual(result["trades"][0]["reason"], "GAP_STOP")
        self.assertEqual(result["trades"][0]["exit"], bars[entry + 1]["open"])

    def test_higher_costs_reduce_equity(self):
        bars, config = sample()
        low = backtest(bars, 0, len(bars) * HOUR_MS, replace(config, fee=0.0001, slippage=0.0001))
        high = backtest(bars, 0, len(bars) * HOUR_MS, replace(config, fee=0.001, slippage=0.001))
        self.assertLess(high["ending_equity"], low["ending_equity"])


if __name__ == "__main__":
    unittest.main()
