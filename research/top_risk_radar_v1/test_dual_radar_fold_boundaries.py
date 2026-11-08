"""Synthetic temporal boundary and fold-disjointness QA for both XRP radars.

No market data, model fitting, performance backtest, or trading.
"""
import unittest
from datetime import datetime, timedelta, timezone
from research.top_risk_radar_v1.walkforward import expanding_calendar_folds

UTC = timezone.utc
def dt(y, m=1, d=1, h=0):
    return datetime(y, m, d, h, tzinfo=UTC)

class DualRadarFoldBoundaryTests(unittest.TestCase):
    def test_exact_maturity_boundary_is_inclusive_for_both_horizons(self):
        for horizon in (14, 30):
            with self.subTest(horizon=horizon):
                boundary = dt(2022)
                ds = [boundary - timedelta(days=horizon),
                      boundary - timedelta(days=horizon) + timedelta(seconds=1),
                      boundary, boundary + timedelta(days=1)]
                f = expanding_calendar_folds(ds, label_horizon=timedelta(days=horizon),
                                             as_of=dt(2023))[0]
                self.assertEqual(f.train_indices, (0,))
                self.assertEqual(f.test_indices, (2, 3))
                self.assertTrue(set(f.train_indices).isdisjoint(f.test_indices))

    def test_exact_asof_maturity_is_included_and_one_second_later_excluded(self):
        for horizon in (14, 30):
            with self.subTest(horizon=horizon):
                as_of = dt(2026, 11, 8)
                ds = [as_of - timedelta(days=horizon),
                      as_of - timedelta(days=horizon) + timedelta(seconds=1)]
                f = expanding_calendar_folds(ds, label_horizon=timedelta(days=horizon),
                                             as_of=as_of)[-1]
                self.assertEqual(f.test_indices, (0,))
                self.assertEqual(f.excluded_unmatured, (1,))

    def test_no_future_year_evaluation_even_with_future_decisions(self):
        ds = [dt(2026, 12, 31), dt(2027)]
        f = expanding_calendar_folds(ds, label_horizon=timedelta(days=14),
                                     as_of=dt(2026, 11, 8))[-1]
        self.assertEqual(f.test_indices, ())
        self.assertEqual(f.excluded_unmatured, (0,))
        self.assertNotIn(1, f.test_indices + f.excluded_unmatured)

    def test_input_order_does_not_change_membership(self):
        ds = [dt(2022, 6), dt(2021, 10), dt(2022, 12), dt(2021, 12, 31)]
        f = expanding_calendar_folds(ds, label_horizon=timedelta(days=14),
                                     as_of=dt(2023))[0]
        self.assertEqual(f.train_indices, (1,))
        self.assertEqual(f.test_indices, (0, 2))

    def test_reject_non_utc_asof_and_decisions(self):
        plus_one = timezone(timedelta(hours=1))
        for horizon in (14, 30):
            with self.subTest(horizon=horizon):
                with self.assertRaises(ValueError):
                    expanding_calendar_folds([dt(2022)], label_horizon=timedelta(days=horizon),
                                             as_of=datetime(2023, 1, 1, tzinfo=plus_one))
                with self.assertRaises(ValueError):
                    expanding_calendar_folds([datetime(2022, 1, 1, tzinfo=plus_one)],
                                             label_horizon=timedelta(days=horizon),
                                             as_of=dt(2023))

if __name__ == "__main__":
    unittest.main()
