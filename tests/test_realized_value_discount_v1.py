import unittest
from dataclasses import replace
from research.realized_value_discount_v1 import Config, DAY, backtest, signal_at


def row(i, p=1.0, m=1.1):
    return dict(timestamp=i * DAY, open=p, high=p * 1.02, low=p * .98, close=p, mvrv=m)


class Tests(unittest.TestCase):
    def test_metric_lag(self):
        r = [row(i) for i in range(50)]
        r[20]["mvrv"] = .8
        self.assertFalse(signal_at(r, 20))
        self.assertTrue(signal_at(r, 21))

    def test_entry_timing_and_no_overlap(self):
        r = [row(i, m=.8) for i in range(100)]
        t, _ = backtest(r, 0, 100 * DAY, replace(Config(), max_hold=2, fee=0, slippage=0))
        self.assertTrue(t)
        self.assertTrue(all(x["entry_timestamp"] == x["metric_timestamp"] + 2 * DAY for x in t))
        self.assertTrue(all(b["entry_timestamp"] > a["exit_timestamp"] for a, b in zip(t, t[1:])))

    def test_costs_hurt(self):
        r = [row(i, m=.8) for i in range(50)]
        a, _ = backtest(r, 0, 50 * DAY, replace(Config(), max_hold=2, fee=0, slippage=0))
        b, _ = backtest(r, 0, 50 * DAY, replace(Config(), max_hold=2))
        self.assertLess(sum(x["pnl"] for x in b), sum(x["pnl"] for x in a))

    def test_gap_stop_worse_open(self):
        r = [row(i, m=.8) for i in range(50)]
        r[17].update(open=.8, high=.9, low=.79, close=.85)
        t, _ = backtest(r, 0, 50 * DAY)
        self.assertEqual(t[0]["reason"], "GAP_STOP")
        self.assertEqual(t[0]["raw_exit"], .8)

    def test_gap_suppresses_signal(self):
        r = [row(i, m=.8) for i in range(50)]
        del r[20]
        self.assertFalse(signal_at(r, 20))

    def test_position_cap(self):
        r = [row(i, m=.8) for i in range(50)]
        t, _ = backtest(r, 0, 50 * DAY)
        self.assertTrue(all(x["leg_notional"] <= .2 * x["entry_equity"] + 1e-8 for x in t))


if __name__ == "__main__":
    unittest.main()
