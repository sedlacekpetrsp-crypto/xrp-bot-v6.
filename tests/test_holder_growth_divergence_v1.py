import unittest
from dataclasses import replace
from research.holder_growth_divergence_v1 import Config, DAY, backtest, signal_at


def row(i, p=1.0, holders=1000.0):
    return dict(timestamp=i * DAY, open=p, high=p * 1.02, low=p * .98, close=p, holders=holders)


def divergent(n=100):
    return [row(i, p=1 if i < 32 else .8, holders=1000 + 2 * i) for i in range(n)]


class Tests(unittest.TestCase):
    def test_joint_signal_and_metric_lag(self):
        r = divergent()
        self.assertFalse(signal_at(r, 31))
        self.assertTrue(signal_at(r, 32))
        r[32]["close"] = 1.0
        self.assertFalse(signal_at(r, 32))

    def test_entry_timing_and_no_overlap(self):
        r = divergent()
        t, _ = backtest(r, 0, 100 * DAY, replace(Config(), max_hold=2, fee=0, slippage=0))
        self.assertTrue(t)
        self.assertTrue(all(x["entry_timestamp"] == x["metric_timestamp"] + 2 * DAY for x in t))
        self.assertTrue(all(b["entry_timestamp"] > a["exit_timestamp"] for a, b in zip(t, t[1:])))

    def test_costs_hurt(self):
        r = divergent(70)
        a, _ = backtest(r, 0, 70 * DAY, replace(Config(), max_hold=2, fee=0, slippage=0))
        b, _ = backtest(r, 0, 70 * DAY, replace(Config(), max_hold=2))
        self.assertLess(sum(x["pnl"] for x in b), sum(x["pnl"] for x in a))

    def test_gap_stop_worse_open(self):
        r = divergent(70)
        r[34].update(open=.5, high=.6, low=.49, close=.55)
        t, _ = backtest(r, 0, 70 * DAY)
        self.assertEqual(t[0]["reason"], "GAP_STOP")
        self.assertEqual(t[0]["raw_exit"], .5)

    def test_gap_suppresses_signal(self):
        r = divergent(70)
        del r[20]
        self.assertFalse(signal_at(r, 31))

    def test_position_cap(self):
        r = divergent(70)
        t, _ = backtest(r, 0, 70 * DAY)
        self.assertTrue(t)
        self.assertTrue(all(x["leg_notional"] <= .2 * x["entry_equity"] + 1e-8 for x in t))


if __name__ == "__main__":
    unittest.main()
