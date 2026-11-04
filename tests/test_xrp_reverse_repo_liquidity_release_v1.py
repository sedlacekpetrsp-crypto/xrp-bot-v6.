import unittest
from dataclasses import replace

from research.xrp_reverse_repo_liquidity_release_v1 import Config, DAY, backtest, make_signals, signal_at


def price(i, p=1.0):
    return dict(timestamp=i * DAY, open=p, high=p * 1.02, low=p * .98, close=p, macro_signal=False)


def declining(n=100):
    macro = [dict(timestamp=i * DAY, value=max(0.0, 200.0 - 2.0 * i)) for i in range(n)]
    signals = make_signals(macro)
    rows = [price(i) for i in range(n)]
    for timestamp, signal in signals.items():
        rows[timestamp // DAY].update(macro_signal=True, **signal)
    return macro, rows


class Tests(unittest.TestCase):
    def test_lag_lookback_and_threshold(self):
        macro, _ = declining(50)
        signals = make_signals(macro)
        self.assertNotIn(21 * DAY, signals)
        self.assertIn(22 * DAY, signals)
        signal = signals[22 * DAY]
        self.assertEqual(signal["metric_timestamp"], 20 * DAY)
        self.assertEqual(signal["earlier_timestamp"], 0)
        self.assertAlmostEqual(signal["rrp_change"], -0.2)

    def test_minimum_start_balance(self):
        macro = [dict(timestamp=i * DAY, value=max(1.0, 90.0 - i)) for i in range(50)]
        self.assertFalse(make_signals(macro))

    def test_entry_timing_and_nonoverlap(self):
        _, rows = declining()
        trades, _ = backtest(rows, 0, 100 * DAY, replace(Config(), max_hold=2, fee=0, slippage=0))
        self.assertTrue(trades)
        self.assertTrue(all(x["entry_timestamp"] == x["signal_timestamp"] + DAY for x in trades))
        self.assertTrue(all(b["entry_timestamp"] > a["exit_timestamp"] for a, b in zip(trades, trades[1:])))

    def test_cost_stress_hurts_same_flat_path(self):
        _, rows = declining(80)
        base, _ = backtest(rows, 0, 80 * DAY, replace(Config(), max_hold=2))
        stress, _ = backtest(rows, 0, 80 * DAY, replace(Config(), max_hold=2, fee=.0019, slippage=.0004))
        self.assertEqual(len(base), len(stress))
        self.assertLess(sum(x["pnl"] for x in stress), sum(x["pnl"] for x in base))

    def test_gap_stop_uses_worse_open(self):
        _, rows = declining(80)
        first_signal = next(i for i, x in enumerate(rows) if x["macro_signal"])
        entry_i = first_signal + 1
        rows[entry_i + 1].update(open=.5, high=.6, low=.49, close=.55)
        trades, _ = backtest(rows, 0, 80 * DAY)
        self.assertEqual(trades[0]["reason"], "GAP_STOP")
        self.assertEqual(trades[0]["raw_exit"], .5)

    def test_price_gap_suppresses_signal_and_atr(self):
        _, rows = declining(80)
        del rows[23]
        self.assertFalse(signal_at(rows, 22))
        trades, _ = backtest(rows, 0, 80 * DAY)
        self.assertTrue(all(x["entry_timestamp"] != 23 * DAY for x in trades))

    def test_position_limits(self):
        _, rows = declining(80)
        trades, _ = backtest(rows, 0, 80 * DAY)
        self.assertTrue(trades)
        self.assertTrue(all(x["leg_notional"] <= .2 * x["entry_equity"] + 1e-8 for x in trades))
        self.assertTrue(all(x["qty"] * (x["entry"] - x["stop"]) <= .005 * x["entry_equity"] + 1e-8 for x in trades))


if __name__ == "__main__":
    unittest.main()

