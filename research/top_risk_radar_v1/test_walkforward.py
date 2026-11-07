import unittest
from datetime import datetime,timedelta,timezone
from research.top_risk_radar_v1.walkforward import expanding_calendar_folds

def t(y,m=1,d=1):
    return datetime(y,m,d,tzinfo=timezone.utc)

class WalkForwardTests(unittest.TestCase):
    def test_purge_14_days(self):
        ds=[t(2021,12,15),t(2021,12,25),t(2022,1,1)]
        f=expanding_calendar_folds(ds,label_horizon=timedelta(days=14),as_of=t(2023))[0]
        self.assertEqual(f.train_indices,(0,))
        self.assertEqual(f.test_indices,(2,))
    def test_purge_30_days(self):
        ds=[t(2021,11,30),t(2021,12,15),t(2022,1,1)]
        f=expanding_calendar_folds(ds,label_horizon=timedelta(days=30),as_of=t(2023))[0]
        self.assertEqual(f.train_indices,(0,))
    def test_unmatured_not_tested(self):
        ds=[t(2026,10,1),t(2026,11,1)]
        f=expanding_calendar_folds(ds,label_horizon=timedelta(days=30),as_of=t(2026,11,8))[-1]
        self.assertEqual(f.test_indices,(0,))
        self.assertEqual(f.excluded_unmatured,(1,))
    def test_reject_naive_timestamp(self):
        with self.assertRaises(ValueError):
            expanding_calendar_folds([datetime(2022,1,1)],label_horizon=timedelta(days=14),as_of=t(2023))
    def test_reject_zero_horizon(self):
        with self.assertRaises(ValueError):
            expanding_calendar_folds([],label_horizon=timedelta(0),as_of=t(2023))
