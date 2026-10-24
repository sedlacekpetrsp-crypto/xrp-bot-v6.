import unittest

from research.bnb_volume_dryup_v1 import Config, HOUR_MS, backtest, signal, with_double_costs


def sample(hours=180):
    bars = []
    price = 100.0
    for i in range(hours):
        opened = price
        price *= 0.999 if i < 100 else 1.0002
        bars.append({"timestamp": i * HOUR_MS, "open": opened, "high": max(opened, price) * 1.001,
                     "low": min(opened, price) * 0.999, "close": price,
                     "quote_volume": 1000.0 if i < 90 else 300.0})
    return bars


class BnbVolumeDryupTests(unittest.TestCase):
    def test_signal_uses_completed_contiguous_history(self):
        bars = sample()
        config = Config(maximum_return=-0.02)
        setup = signal(bars, 95, config)
        self.assertIsNotNone(setup)
        self.assertLessEqual(setup["volume_ratio"], config.maximum_volume_ratio)
        broken = bars.copy()
        broken[80] = {**broken[80], "timestamp": broken[80]["timestamp"] + 2 * HOUR_MS}
        with self.assertRaises(ValueError):
            backtest(broken, 0, len(broken) * HOUR_MS, config)

    def test_entry_is_next_bar_and_positions_do_not_overlap(self):
        config = Config(maximum_return=-0.02, maximum_hold_hours=8, cooldown_hours=4,
                        stop_loss=0.5, take_profit=0.5, fee_rate=0, slippage_rate=0)
        result = backtest(sample(260), 0, 260 * HOUR_MS, config)
        self.assertTrue(result["trades"])
        first_entry = result["trades"][0]["entry_ts"] // HOUR_MS
        self.assertGreaterEqual(first_entry, config.recent_volume_hours + config.baseline_volume_hours)
        self.assertIsNotNone(signal(sample(260), first_entry - 1, config))
        for prior, later in zip(result["trades"], result["trades"][1:]):
            self.assertGreaterEqual(later["entry_ts"], prior["exit_ts"] + config.cooldown_hours * HOUR_MS)

    def test_gap_stop_uses_worse_open(self):
        data = sample(180)
        config = Config(maximum_return=-0.02, stop_loss=0.04, take_profit=0.5, fee_rate=0, slippage_rate=0)
        baseline = backtest(data, 0, 180 * HOUR_MS, config)
        entry_index = baseline["trades"][0]["entry_ts"] // HOUR_MS
        data[entry_index + 1]["open"] = 50.0
        data[entry_index + 1]["low"] = 50.0
        data[entry_index + 1]["high"] = max(50.0, data[entry_index + 1]["high"])
        result = backtest(data, 0, 180 * HOUR_MS, config)
        self.assertEqual(result["trades"][0]["reason"], "GAP_STOP")
        self.assertEqual(result["trades"][0]["exit"], 50.0)

    def test_double_costs_reduce_equity(self):
        config = Config(maximum_return=-0.02, stop_loss=0.5, take_profit=0.5)
        self.assertLess(backtest(sample(260), 0, 260 * HOUR_MS, with_double_costs(config))["ending_equity"],
                        backtest(sample(260), 0, 260 * HOUR_MS, config)["ending_equity"])


if __name__ == "__main__":
    unittest.main()
