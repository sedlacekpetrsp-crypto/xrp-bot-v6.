import unittest
from dataclasses import replace

from research.real_yield_easing_v1 import Config, DAY, backtest, make_signals, signal_at


def row(i, p=1.0):
    return dict(timestamp=i * DAY, open=p, high=p * 1.02, low=p * .98, close=p, macro_signal=False)


def declining(n=80):
    macro = [dict(timestamp=i * DAY, value=1.5 - .02 * i) for i in range(n)]
    signals = make_signals(macro)
    rows = [row(i) for i in range(n)]
    for t, signal in signals.items():
        rows[t // DAY].update(macro_signal=True, **signal)
    return macro, rows


class Tests(unittest.TestCase):
    def test_arithmetic_change_and_release_lag(self):
        macro, rows = declining()
        signals = make_signals(macro)
        self.assertNotIn(21 * DAY, signals)
        self.assertIn(22 * DAY, signals)
        self.assertEqual(signals[22 * DAY]["metric_timestamp"], 20 * DAY)
        self.assertAlmostEqual(signals[22 * DAY]["macro_return"], -.4)
        self.assertTrue(signal_at(rows, 22))

    def test_negative_real_yield_is_valid(self):
        macro = [dict(timestamp=i * DAY, value=.1 - .02 * i) for i in range(30)]
        self.assertTrue(make_signals(macro))

    def test_entry_timing_and_no_overlap(self):
        _, rows = declining(100)
        trades, _ = backtest(rows, 0, 100 * DAY, replace(Config(), max_hold=2, fee=0, slippage=0))
        self.assertTrue(trades)
        self.assertTrue(all(x["entry_timestamp"] == x["signal_timestamp"] + DAY for x in trades))
        self.assertTrue(all(b["entry_timestamp"] > a["exit_timestamp"] for a, b in zip(trades, trades[1:])))

    def test_costs_hurt(self):
        _, rows = declining(70)
        free, _ = backtest(rows, 0, 70 * DAY, replace(Config(), max_hold=2, fee=0, slippage=0))
        paid, _ = backtest(rows, 0, 70 * DAY, replace(Config(), max_hold=2))
        self.assertLess(sum(x["pnl"] for x in paid), sum(x["pnl"] for x in free))

    def test_gap_stop_uses_worse_open(self):
        _, rows = declining(70)
        rows[24].update(open=.5, high=.6, low=.49, close=.55)
        trades, _ = backtest(rows, 0, 70 * DAY)
        self.assertEqual(trades[0]["reason"], "GAP_STOP")
        self.assertEqual(trades[0]["raw_exit"], .5)

    def test_position_cap(self):
        _, rows = declining(70)
        trades, _ = backtest(rows, 0, 70 * DAY)
        self.assertTrue(all(x["leg_notional"] <= .2 * x["entry_equity"] + 1e-8 for x in trades))

    def test_future_prefix_invariance(self):
        macro, _ = declining(90)
        prefix = make_signals(macro[:60])
        full = make_signals(macro)
        self.assertEqual(prefix, {key: value for key, value in full.items() if key < 60 * DAY})


if __name__ == "__main__":
    unittest.main()
