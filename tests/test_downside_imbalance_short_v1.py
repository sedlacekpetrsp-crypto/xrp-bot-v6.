import unittest
from dataclasses import replace

from research.downside_imbalance_short_v1 import Config, HOUR_MS, SYMBOLS, backtest, signal


def market(closes, opens=None, highs=None, lows=None):
    opens = opens or closes
    highs = highs or [max(o, c) for o, c in zip(opens, closes)]
    lows = lows or [min(o, c) for o, c in zip(opens, closes)]
    bars = [{"timestamp": i * HOUR_MS, "open": o, "high": h, "low": l,
             "close": c, "volume": 1.0}
            for i, (o, h, l, c) in enumerate(zip(opens, highs, lows, closes))]
    return {symbol: [dict(bar) for bar in bars] for symbol in SYMBOLS}


class DownsideImbalanceTests(unittest.TestCase):
    def config(self, **kwargs):
        base = Config(lookback_hours=3, energy_ratio=1.0, minimum_negative_hours=2,
                      maximum_lookback_return=-0.01, maximum_close_location=0.5,
                      stop=0.10, target=0.10, maximum_hold_hours=2,
                      cooldown_hours=0, max_positions=1, position_fraction=0.10,
                      fee=0.0, slippage=0.0, annual_borrow=0.0)
        return replace(base, **kwargs)

    def test_signal_uses_only_completed_bars(self):
        bars = market([100, 99, 98, 96, 150])[SYMBOLS[0]]
        self.assertIsNotNone(signal(bars, 3, self.config()))
        self.assertIsNone(signal(bars, 4, self.config()))

    def test_entry_is_next_open_and_time_exit(self):
        closes = [100, 99, 98, 96, 80, 79, 78]
        opens = [100, 99, 98, 96, 80, 79, 78]
        result = backtest(market(closes, opens), 0, 7 * HOUR_MS, self.config())
        trade = result["trades"][0]
        self.assertEqual(trade["entry_ts"], 4 * HOUR_MS)
        self.assertEqual(trade["entry"], 80)
        self.assertEqual(trade["reason"], "TIME")

    def test_stop_wins_same_bar_ambiguity(self):
        closes = [100, 99, 98, 96, 96]
        opens = [100, 99, 98, 96, 96]
        highs = [100, 99, 98, 96, 110]
        lows = [100, 99, 98, 96, 80]
        result = backtest(market(closes, opens, highs, lows), 0, 5 * HOUR_MS,
                          self.config(stop=0.05, target=0.05))
        self.assertEqual(result["trades"][0]["reason"], "STOP")

    def test_gap_stop_fills_at_worse_open(self):
        closes = [100, 99, 98, 96, 96, 120]
        opens = [100, 99, 98, 96, 96, 120]
        highs = [100, 99, 98, 96, 96, 120]
        lows = [100, 99, 98, 96, 96, 120]
        result = backtest(market(closes, opens, highs, lows), 0, 6 * HOUR_MS,
                          self.config(stop=0.10, maximum_hold_hours=5))
        trade = result["trades"][0]
        self.assertEqual(trade["reason"], "GAP_STOP")
        self.assertEqual(trade["exit"], 120)

    def test_costs_are_deducted_and_borrow_recorded(self):
        result = backtest(market([100, 99, 98, 96, 96, 96, 96]), 0, 7 * HOUR_MS,
                          self.config(fee=0.001, annual_borrow=0.0876))
        trade = result["trades"][0]
        self.assertGreater(trade["fees"], 0)
        self.assertGreater(trade["borrow_cost"], 0)
        self.assertAlmostEqual(trade["net_pnl"], trade["gross_pnl"] - trade["fees"]
                               - trade["borrow_cost"], places=10)


if __name__ == "__main__":
    unittest.main()
