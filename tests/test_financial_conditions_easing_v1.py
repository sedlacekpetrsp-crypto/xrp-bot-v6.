import unittest
from dataclasses import replace

from research.financial_conditions_easing_v1 import Config, DAY, backtest, make_signals, signal_at

WEEK = 7 * DAY


def macro_rows(n=40):
    return [{"timestamp": i * WEEK, "value": -.1 - .02 * i} for i in range(n)]


def daily_rows(n=300):
    return [{"timestamp": i * DAY, "open": 1.0, "high": 1.02, "low": .98, "close": 1.0, "macro_signal": False} for i in range(n)]


def joined():
    macro = macro_rows()
    rows = daily_rows()
    for timestamp, signal in make_signals(macro).items():
        rows[timestamp // DAY].update(macro_signal=True, **signal)
    return macro, rows


class Tests(unittest.TestCase):
    def test_level_change_and_release_lag(self):
        macro, rows = joined()
        signals = make_signals(macro)
        self.assertNotIn(9 * WEEK, signals)
        self.assertIn(10 * WEEK, signals)
        self.assertEqual(signals[10 * WEEK]["metric_timestamp"], 8 * WEEK)
        self.assertLessEqual(signals[10 * WEEK]["macro_level"], -.25)
        self.assertAlmostEqual(signals[10 * WEEK]["macro_return"], -.16)
        self.assertTrue(signal_at(rows, 70))

    def test_both_filters_required(self):
        flat = [{"timestamp": i * WEEK, "value": -.5} for i in range(30)]
        high = [{"timestamp": i * WEEK, "value": .1 - .02 * i} for i in range(12)]
        self.assertFalse(make_signals(flat))
        self.assertFalse(make_signals(high))

    def test_prefix_invariance(self):
        macro = macro_rows(40)
        prefix = make_signals(macro[:25])
        full = make_signals(macro)
        self.assertEqual(prefix, {key: value for key, value in full.items() if key < 25 * WEEK})

    def test_next_open_and_no_overlap(self):
        _, rows = joined()
        trades, _ = backtest(rows, 0, len(rows) * DAY, replace(Config(), max_hold=10, fee=0, slippage=0))
        self.assertTrue(trades)
        self.assertTrue(all(item["entry_timestamp"] == item["signal_timestamp"] + DAY for item in trades))
        self.assertTrue(all(b["entry_timestamp"] > a["exit_timestamp"] for a, b in zip(trades, trades[1:])))

    def test_costs_hurt(self):
        _, rows = joined()
        free, _ = backtest(rows, 0, len(rows) * DAY, replace(Config(), max_hold=2, fee=0, slippage=0))
        paid, _ = backtest(rows, 0, len(rows) * DAY, replace(Config(), max_hold=2))
        self.assertLess(sum(item["pnl"] for item in paid), sum(item["pnl"] for item in free))

    def test_gap_stop_and_position_cap(self):
        _, rows = joined()
        rows[72].update(open=.5, high=.6, low=.49, close=.55)
        trades, _ = backtest(rows, 0, len(rows) * DAY, Config())
        self.assertEqual(trades[0]["reason"], "GAP_STOP")
        self.assertEqual(trades[0]["raw_exit"], .5)
        self.assertTrue(all(item["leg_notional"] <= .2 * item["entry_equity"] + 1e-8 for item in trades))


if __name__ == "__main__":
    unittest.main()
