import unittest
from dataclasses import replace

from research.xrp_yield_curve_steepening_v1 import Config, DAY, backtest, make_signals, signal_at


def price(index, value=1.0):
    return dict(timestamp=index * DAY, open=value, high=value * 1.02, low=value * .98, close=value, macro_signal=False)


def rising(count=100):
    macro = [dict(timestamp=i * DAY, value=-1.0 + .02 * i) for i in range(count)]
    signals = make_signals(macro)
    rows = [price(i) for i in range(count)]
    for timestamp, signal in signals.items():
        rows[timestamp // DAY].update(macro_signal=True, **signal)
    return macro, rows


class Tests(unittest.TestCase):
    def test_lag_lookback_negative_levels_and_threshold(self):
        macro, _ = rising(50)
        signals = make_signals(macro)
        self.assertNotIn(21 * DAY, signals)
        signal = signals[22 * DAY]
        self.assertEqual(signal["metric_timestamp"], 20 * DAY)
        self.assertEqual(signal["earlier_timestamp"], 0)
        self.assertAlmostEqual(signal["spread_change"], .4)

    def test_below_threshold_has_no_signal(self):
        macro = [dict(timestamp=i * DAY, value=-.5 + .01 * i) for i in range(50)]
        self.assertFalse(make_signals(macro))

    def test_entry_timing_and_nonoverlap(self):
        _, rows = rising()
        trades, _ = backtest(rows, 0, 100 * DAY, replace(Config(), max_hold=2, fee=0, slippage=0))
        self.assertTrue(trades)
        self.assertTrue(all(x["entry_timestamp"] == x["signal_timestamp"] + DAY for x in trades))
        self.assertTrue(all(b["entry_timestamp"] > a["exit_timestamp"] for a, b in zip(trades, trades[1:])))

    def test_stress_costs_hurt_flat_path(self):
        _, rows = rising(80)
        base, _ = backtest(rows, 0, 80 * DAY, replace(Config(), max_hold=2))
        stress, _ = backtest(rows, 0, 80 * DAY, replace(Config(), max_hold=2, fee=.0019, slippage=.0004))
        self.assertEqual(len(base), len(stress))
        self.assertLess(sum(x["pnl"] for x in stress), sum(x["pnl"] for x in base))

    def test_gap_stop_worse_open(self):
        _, rows = rising(80)
        signal_i = next(i for i, row in enumerate(rows) if row["macro_signal"])
        rows[signal_i + 2].update(open=.5, high=.6, low=.49, close=.55)
        trades, _ = backtest(rows, 0, 80 * DAY)
        self.assertEqual(trades[0]["reason"], "GAP_STOP")
        self.assertEqual(trades[0]["raw_exit"], .5)

    def test_gap_suppresses_entry_and_atr(self):
        _, rows = rising(80)
        del rows[23]
        self.assertFalse(signal_at(rows, 22))
        trades, _ = backtest(rows, 0, 80 * DAY)
        self.assertTrue(all(x["entry_timestamp"] != 23 * DAY for x in trades))

    def test_position_limits(self):
        _, rows = rising(80)
        trades, _ = backtest(rows, 0, 80 * DAY)
        self.assertTrue(trades)
        self.assertTrue(all(x["leg_notional"] <= .2 * x["entry_equity"] + 1e-8 for x in trades))
        self.assertTrue(all(x["qty"] * (x["entry"] - x["stop"]) <= .005 * x["entry_equity"] + 1e-8 for x in trades))


if __name__ == "__main__":
    unittest.main()

