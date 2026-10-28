import unittest
from dataclasses import replace
from research.vix_shock_recovery_v1 import Config, DAY, backtest, make_signals, signal_at


def row(i, p=1.0):
    return dict(timestamp=i * DAY, open=p, high=p * 1.02, low=p * .98, close=p, macro_signal=False)


def recovering(n=80):
    macro = [dict(timestamp=i * DAY, value=30 if i % 10 < 5 else 20) for i in range(n)]
    signals = make_signals(macro)
    rows = [row(i) for i in range(n)]
    for t, signal in signals.items():
        rows[t // DAY].update(macro_signal=True, **signal)
    return macro, rows


class Tests(unittest.TestCase):
    def test_vix_recovery_and_release_lag(self):
        macro, rows = recovering()
        signals = make_signals(macro)
        self.assertNotIn(6 * DAY, signals)
        self.assertIn(7 * DAY, signals)
        self.assertEqual(signals[7 * DAY]["metric_timestamp"], 5 * DAY)
        self.assertEqual(signals[7 * DAY]["vix_prior"], 30)
        self.assertTrue(signal_at(rows, 7))

    def test_entry_timing_and_no_overlap(self):
        _, r = recovering(100)
        t, _ = backtest(r, 0, 100 * DAY, replace(Config(), max_hold=2, fee=0, slippage=0))
        self.assertTrue(t)
        self.assertTrue(all(x["entry_timestamp"] == x["signal_timestamp"] + DAY for x in t))
        self.assertTrue(all(b["entry_timestamp"] > a["exit_timestamp"] for a, b in zip(t, t[1:])))

    def test_costs_hurt(self):
        _, r = recovering(70)
        a, _ = backtest(r, 0, 70 * DAY, replace(Config(), max_hold=2, fee=0, slippage=0))
        b, _ = backtest(r, 0, 70 * DAY, replace(Config(), max_hold=2))
        self.assertLess(sum(x["pnl"] for x in b), sum(x["pnl"] for x in a))

    def test_gap_stop_worse_open(self):
        _, r = recovering(70)
        r[19].update(open=.5, high=.6, low=.49, close=.55)
        t, _ = backtest(r, 0, 70 * DAY)
        self.assertEqual(t[0]["reason"], "GAP_STOP")
        self.assertEqual(t[0]["raw_exit"], .5)

    def test_gap_suppresses_signal(self):
        _, r = recovering(70)
        del r[18]
        self.assertFalse(signal_at(r, 17))

    def test_position_cap(self):
        _, r = recovering(70)
        t, _ = backtest(r, 0, 70 * DAY)
        self.assertTrue(t)
        self.assertTrue(all(x["leg_notional"] <= .2 * x["entry_equity"] + 1e-8 for x in t))


if __name__ == "__main__":
    unittest.main()
