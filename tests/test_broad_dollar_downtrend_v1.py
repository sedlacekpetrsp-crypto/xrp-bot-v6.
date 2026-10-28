import unittest
from dataclasses import replace
from research.broad_dollar_downtrend_v1 import Config, DAY, backtest, make_signals, signal_at


def row(i, p=1.0):
    return dict(timestamp=i * DAY, open=p, high=p * 1.02, low=p * .98, close=p, macro_signal=False)


def declining(n=80):
    macro = [dict(timestamp=i * DAY, value=100 - .1 * i) for i in range(n)]
    signals = make_signals(macro)
    rows = [row(i) for i in range(n)]
    for t, signal in signals.items():
        rows[t // DAY].update(macro_signal=True, **signal)
    return macro, rows


class Tests(unittest.TestCase):
    def test_macro_lookback_and_release_lag(self):
        macro, rows = declining()
        signals = make_signals(macro)
        self.assertNotIn(21 * DAY, signals)
        self.assertIn(22 * DAY, signals)
        self.assertEqual(signals[22 * DAY]["metric_timestamp"], 20 * DAY)
        self.assertTrue(signal_at(rows, 22))

    def test_entry_timing_and_no_overlap(self):
        _, r = declining(100)
        t, _ = backtest(r, 0, 100 * DAY, replace(Config(), max_hold=2, fee=0, slippage=0))
        self.assertTrue(t)
        self.assertTrue(all(x["entry_timestamp"] == x["signal_timestamp"] + DAY for x in t))
        self.assertTrue(all(b["entry_timestamp"] > a["exit_timestamp"] for a, b in zip(t, t[1:])))

    def test_costs_hurt(self):
        _, r = declining(70)
        a, _ = backtest(r, 0, 70 * DAY, replace(Config(), max_hold=2, fee=0, slippage=0))
        b, _ = backtest(r, 0, 70 * DAY, replace(Config(), max_hold=2))
        self.assertLess(sum(x["pnl"] for x in b), sum(x["pnl"] for x in a))

    def test_gap_stop_worse_open(self):
        _, r = declining(70)
        r[24].update(open=.5, high=.6, low=.49, close=.55)
        t, _ = backtest(r, 0, 70 * DAY)
        self.assertEqual(t[0]["reason"], "GAP_STOP")
        self.assertEqual(t[0]["raw_exit"], .5)

    def test_gap_suppresses_signal(self):
        _, r = declining(70)
        del r[23]
        self.assertFalse(signal_at(r, 22))

    def test_position_cap(self):
        _, r = declining(70)
        t, _ = backtest(r, 0, 70 * DAY)
        self.assertTrue(t)
        self.assertTrue(all(x["leg_notional"] <= .2 * x["entry_equity"] + 1e-8 for x in t))


if __name__ == "__main__":
    unittest.main()
