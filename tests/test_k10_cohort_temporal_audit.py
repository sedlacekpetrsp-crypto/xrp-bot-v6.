import unittest
from datetime import datetime, timedelta, timezone
from research.k10_cohort_temporal_audit import CohortWindow, validate_cohort_window

T = datetime(2023, 1, 1, tzinfo=timezone.utc)
def window(**overrides):
    values = dict(sample_start=T, ranking_start=T-timedelta(days=90),
                  ranking_end=T-timedelta(days=1),
                  ledger_closed_at=T-timedelta(hours=12),
                  first_observed_at=T-timedelta(hours=6))
    values.update(overrides)
    return CohortWindow(**values)

class CohortTemporalAuditTests(unittest.TestCase):
    def test_valid(self): self.assertTrue(validate_cohort_window(window()))
    def test_ranking_overlap(self):
        with self.assertRaises(ValueError): validate_cohort_window(window(ranking_end=T))
    def test_late_first_observation(self):
        with self.assertRaises(ValueError): validate_cohort_window(window(first_observed_at=T+timedelta(seconds=1)))
    def test_unfinalized_ledger(self):
        with self.assertRaises(ValueError): validate_cohort_window(window(ledger_closed_at=T))
    def test_reversed_ranking(self):
        with self.assertRaises(ValueError): validate_cohort_window(window(ranking_start=T))
    def test_naive_timestamp(self):
        with self.assertRaises(ValueError): validate_cohort_window(window(first_observed_at=T.replace(tzinfo=None)))
    def test_observation_before_ledger_close(self):
        with self.assertRaises(ValueError): validate_cohort_window(window(first_observed_at=T-timedelta(days=2)))

if __name__ == "__main__": unittest.main()
