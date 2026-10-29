import unittest
from dataclasses import replace

from research.extreme_fear_contrarian_v1 import Config, DAY, backtest, signal_at


def row(index, fear=50, price=1.0):
    return {"timestamp": index * DAY, "open": price, "high": price * 1.02, "low": price * .98, "close": price, "fear": fear}


def fearful(n=80):
    return [row(i, 15 if i >= 15 else 50) for i in range(n)]


class Tests(unittest.TestCase):
    def test_full_day_lag_and_next_open(self):
        rows = fearful()
        self.assertFalse(signal_at(rows, 15))
        self.assertTrue(signal_at(rows, 16))
        trades, _ = backtest(rows, 0, len(rows) * DAY, replace(Config(), max_hold=2, fee=0, slippage=0))
        self.assertEqual(trades[0]["signal_timestamp"], 16 * DAY)
        self.assertEqual(trades[0]["metric_timestamp"], 15 * DAY)
        self.assertEqual(trades[0]["entry_timestamp"], 17 * DAY)

    def test_threshold_is_inclusive(self):
        rows = [row(i, 20 if i == 15 else 50) for i in range(30)]
        self.assertTrue(signal_at(rows, 16))
        rows[15]["fear"] = 21
        self.assertFalse(signal_at(rows, 16))

    def test_prefix_invariance(self):
        rows = fearful(60)
        prefix = [signal_at(rows[:40], i) for i in range(39)]
        full = [signal_at(rows, i) for i in range(39)]
        self.assertEqual(prefix, full)

    def test_costs_hurt_and_no_overlap(self):
        rows = fearful()
        free, _ = backtest(rows, 0, len(rows) * DAY, replace(Config(), max_hold=2, fee=0, slippage=0))
        paid, _ = backtest(rows, 0, len(rows) * DAY, replace(Config(), max_hold=2))
        self.assertLess(sum(item["pnl"] for item in paid), sum(item["pnl"] for item in free))
        self.assertTrue(all(b["entry_timestamp"] > a["exit_timestamp"] for a, b in zip(paid, paid[1:])))

    def test_gap_stop_and_position_cap(self):
        rows = fearful()
        rows[18].update(open=.5, high=.6, low=.49, close=.55)
        trades, _ = backtest(rows, 0, len(rows) * DAY)
        self.assertEqual(trades[0]["reason"], "GAP_STOP")
        self.assertEqual(trades[0]["raw_exit"], .5)
        self.assertTrue(all(item["leg_notional"] <= .2 * item["entry_equity"] + 1e-8 for item in trades))

    def test_missing_day_suppresses(self):
        rows = fearful()
        del rows[15]
        self.assertFalse(signal_at(rows, 15))


if __name__ == "__main__":
    unittest.main()
