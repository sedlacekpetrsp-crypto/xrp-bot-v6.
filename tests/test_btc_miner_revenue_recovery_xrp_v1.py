import unittest

from research.btc_miner_revenue_recovery_xrp_v1 import DAY, backtest, execution_config, make_signals


def bars(n=120, price=100.0):
    return [{"timestamp": i * DAY, "open": price, "high": price + 1, "low": price - 1, "close": price} for i in range(n)]


def signal(row):
    row.update(macro_signal=True, metric_timestamp=12 * DAY, window_start_timestamp=0, prior_median=90, latest_miner_revenue=120, recent7_mean=115, previous7_mean=105)


class MinerRevenueTests(unittest.TestCase):
    def test_strict_past_median_lag_and_trend(self):
        values = [100.0] * 84 + [101, 103, 105, 107, 109, 111, 113] + [115] * 9
        rows = [{"timestamp": i * DAY, "value": value} for i, value in enumerate(values)]
        signals = make_signals(rows)
        self.assertIn(92 * DAY, signals)
        self.assertEqual(signals[92 * DAY]["metric_timestamp"], 90 * DAY)
        self.assertEqual(signals[92 * DAY]["window_start_timestamp"], 0)

    def test_flat_series_rejected(self):
        rows = [{"timestamp": i * DAY, "value": 100} for i in range(100)]
        self.assertFalse(make_signals(rows))

    def test_invalid_source_rejected(self):
        with self.assertRaises(ValueError):
            make_signals([{"timestamp": 1, "value": 1}, {"timestamp": 0, "value": 1}])

    def test_next_open_and_notional_cap(self):
        rows = bars(); signal(rows[14])
        trades, _ = backtest(rows, 0, 120 * DAY, execution_config())
        self.assertEqual(trades[0]["entry_timestamp"], 15 * DAY)
        self.assertLessEqual(trades[0]["leg_notional"], 2000.000001)

    def test_gap_stop(self):
        rows = bars(); signal(rows[14]); rows[16].update(open=90, high=101, low=89, close=100)
        trades, _ = backtest(rows, 0, 120 * DAY, execution_config())
        self.assertEqual(trades[0]["reason"], "GAP_STOP")

    def test_double_cost_is_worse(self):
        rows = bars(); signal(rows[14])
        base, _ = backtest(rows, 0, 120 * DAY, execution_config())
        stress, _ = backtest(rows, 0, 120 * DAY, execution_config(2))
        self.assertLess(stress[0]["pnl"], base[0]["pnl"])

    def test_drawdown_marks_open_position(self):
        rows = bars(); signal(rows[14])
        trades, curve = backtest(rows, 0, 120 * DAY, execution_config())
        self.assertIn(trades[0]["intratrade_min_equity"], [point["equity"] for point in curve])


if __name__ == "__main__":
    unittest.main()
