import unittest
from dataclasses import replace
from research.btc_mempool_clearance_xrp_v1 import Config, DAY, aggregate_daily, backtest, lower_tercile, make_signals


def metric(n=390):
    return [dict(timestamp=i * DAY, mempool_bytes=1000.0, samples=96) for i in range(n)]


def bars(n=430):
    return [dict(timestamp=i * DAY, open=100.0, high=101.0, low=99.0, close=100.0) for i in range(n)]


class Tests(unittest.TestCase):
    def test_daily_median_and_minimum_count(self):
        points = [dict(timestamp=i * 900_000, mempool_bytes=float(i)) for i in range(96)]
        row = aggregate_daily(points)[0]
        self.assertEqual(row["samples"], 96)
        self.assertEqual(row["mempool_bytes"], 47.5)
        with self.assertRaises(ValueError):
            aggregate_daily(points[:63])

    def test_duplicate_or_gap_rejected(self):
        points = [dict(timestamp=i * 900_000, mempool_bytes=1.0) for i in range(96)]
        with self.assertRaises(ValueError):
            aggregate_daily(points + [points[-1]])
        m = metric()
        del m[10]
        with self.assertRaises(ValueError):
            make_signals(m)

    def test_strict_past_window_and_empirical_tercile(self):
        m = metric()
        friday = next(i for i in range(365, 372) if i % 7 == 1)  # epoch day 1 is Friday
        m[friday]["mempool_bytes"] = 10.0
        signals = make_signals(m)
        signal = signals[(friday + 3) * DAY]
        self.assertEqual(signal["metric_timestamp"], friday * DAY)
        self.assertEqual(signal["cutoff365"], 1000.0)
        self.assertEqual((friday + 3) % 7, 4)  # epoch day 4 is Monday
        self.assertEqual(lower_tercile(range(365)), 121.0)

    def test_future_invariance(self):
        m = metric(400)
        friday = next(i for i in range(365, 372) if i % 7 == 1)
        m[friday]["mempool_bytes"] = 10.0
        a = make_signals(m)
        m[390]["mempool_bytes"] = 1e12
        self.assertEqual({k:v for k,v in a.items() if k < 390 * DAY}, {k:v for k,v in make_signals(m).items() if k < 390 * DAY})

    def test_stop_first_and_double_cost(self):
        m = metric()
        friday = next(i for i in range(365, 372) if i % 7 == 1)
        m[friday]["mempool_bytes"] = 10.0
        entry_day = friday + 3
        r = bars()
        r[entry_day]["mempool_signal"] = make_signals(m)[entry_day * DAY]
        r[entry_day].update(high=120.0, low=80.0)
        a, _ = backtest(r, 0, 10**18)
        b, _ = backtest(r, 0, 10**18, replace(Config(), fee=.0019, slippage=.0004))
        self.assertEqual(a[0]["reason"], "STOP")
        self.assertLess(b[0]["pnl"], a[0]["pnl"])

    def test_gap_stop_sizing_and_cap(self):
        m = metric()
        friday = next(i for i in range(365, 372) if i % 7 == 1)
        m[friday]["mempool_bytes"] = 10.0
        entry_day = friday + 3
        r = bars()
        r[entry_day]["mempool_signal"] = make_signals(m)[entry_day * DAY]
        r[entry_day + 1].update(open=80.0, high=81.0, low=79.0, close=80.0)
        t, _ = backtest(r, 0, 10**18)
        self.assertEqual(t[0]["reason"], "GAP_STOP")
        self.assertLessEqual(t[0]["leg_notional"], 2000.0 + 1e-8)
        self.assertLessEqual(t[0]["qty"] * (t[0]["entry"] - t[0]["stop"]), 50.0 + 1e-8)

    def test_weekly_nonoverlap_and_time_exit(self):
        m = metric(410)
        for i in range(365, 400):
            if i % 7 == 1:
                m[i]["mempool_bytes"] = 10.0
        sig = make_signals(m)
        r = bars(450)
        for t, s in sig.items():
            r[t // DAY]["mempool_signal"] = s
        trades, _ = backtest(r, 0, 10**18)
        self.assertTrue(all(a["exit_timestamp"] < b["entry_timestamp"] for a,b in zip(trades,trades[1:])))
        self.assertTrue(all(x["reason"] == "TIME" for x in trades))

    def test_fold_end_is_realized_not_discarded(self):
        m = metric()
        friday = next(i for i in range(365, 372) if i % 7 == 1)
        m[friday]["mempool_bytes"] = 10.0
        entry_day = friday + 3
        r = bars(entry_day + 3)
        r[entry_day]["mempool_signal"] = make_signals(m)[entry_day * DAY]
        trades, curve = backtest(r, 0, (entry_day + 3) * DAY)
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]["reason"], "FOLD_END")
        self.assertEqual(trades[0]["exit_timestamp"], (entry_day + 2) * DAY)
        self.assertEqual(curve[-1]["equity"], trades[0]["equity"])


if __name__ == "__main__":
    unittest.main()
