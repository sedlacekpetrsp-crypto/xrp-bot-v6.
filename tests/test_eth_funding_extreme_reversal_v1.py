import unittest

from research.eth_funding_extreme_reversal_v1 import Config, HOUR_MS, backtest, funding_signal, with_cost_stress


def sample(hours=96):
    bars = []
    price = 100.0
    for i in range(hours):
        opened = price; price *= 1.0002
        bars.append({"timestamp": i * HOUR_MS, "open": opened, "high": max(opened, price) * 1.002,
                     "low": min(opened, price) * 0.998, "close": price})
    return bars


class FundingExtremeTests(unittest.TestCase):
    def test_signal_is_contrarian_and_threshold_is_inclusive(self):
        config = Config()
        self.assertEqual(funding_signal(config.minimum_absolute_funding, config), -1)
        self.assertEqual(funding_signal(-config.minimum_absolute_funding, config), 1)
        self.assertIsNone(funding_signal(config.minimum_absolute_funding - 1e-8, config))

    def test_entry_is_hour_after_known_funding_and_no_overlap(self):
        rates = {8 * HOUR_MS: 0.001, 16 * HOUR_MS: -0.001, 40 * HOUR_MS: 0.001}
        config = Config(stop_loss=0.5, take_profit=0.5, maximum_hold_hours=8, cooldown_hours=8,
                        fee_rate=0, slippage_rate=0)
        result = backtest(sample(), rates, 0, 96 * HOUR_MS, config)
        self.assertEqual(result["trades"][0]["entry_ts"], 9 * HOUR_MS)
        self.assertEqual(result["trades"][0]["side"], -1)
        for prior, later in zip(result["trades"], result["trades"][1:]):
            self.assertGreaterEqual(later["entry_ts"], prior["exit_ts"] + config.cooldown_hours * HOUR_MS)

    def test_gap_stop_uses_worse_open_for_short(self):
        data = sample(); rates = {8 * HOUR_MS: 0.001}
        config = Config(stop_loss=0.04, take_profit=0.5, fee_rate=0, slippage_rate=0)
        data[10]["open"] = 200.0; data[10]["high"] = 200.0; data[10]["low"] = min(data[10]["low"], 200.0)
        result = backtest(data, rates, 0, 96 * HOUR_MS, config)
        self.assertEqual(result["trades"][0]["reason"], "GAP_STOP")
        self.assertEqual(result["trades"][0]["exit"], 200.0)

    def test_actual_funding_cashflow_is_applied(self):
        rates = {8 * HOUR_MS: 0.001, 16 * HOUR_MS: 0.002}
        config = Config(stop_loss=0.5, take_profit=0.5, maximum_hold_hours=16, fee_rate=0, slippage_rate=0)
        trade = backtest(sample(), rates, 0, 96 * HOUR_MS, config)["trades"][0]
        self.assertGreater(trade["funding_pnl"], 0)

    def test_stress_reduces_equity(self):
        rates = {8 * HOUR_MS: 0.001, 40 * HOUR_MS: -0.001, 72 * HOUR_MS: 0.001}
        config = Config(stop_loss=0.5, take_profit=0.5, maximum_hold_hours=16)
        self.assertLess(backtest(sample(), rates, 0, 96 * HOUR_MS, with_cost_stress(config))["ending_equity"],
                        backtest(sample(), rates, 0, 96 * HOUR_MS, config)["ending_equity"])


if __name__ == "__main__":
    unittest.main()
