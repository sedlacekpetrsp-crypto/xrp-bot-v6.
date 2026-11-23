import unittest
from datetime import datetime, timedelta, timezone

from research.g1_label_maturity_preflight import maturity_mask, fold_maturity_counts

UTC = timezone.utc
T = datetime(2026, 1, 1, tzinfo=UTC)


class MaturityPreflightTests(unittest.TestCase):
    def test_cutoff_boundary_is_inclusive(self):
        self.assertEqual(maturity_mask([T, T + timedelta(seconds=1)], T + timedelta(days=14)), [True, False])

    def test_immature_not_assumed_negative(self):
        self.assertEqual(fold_maturity_counts([T, T + timedelta(days=1)], ["A", "A"], T + timedelta(days=14)), {"A": {"mature": 1, "immature": 1}})

    def test_fold_boundary_does_not_truncate_horizon(self):
        self.assertEqual(fold_maturity_counts([T, T + timedelta(days=1)], ["train", "test"], T + timedelta(days=14)), {"train": {"mature": 1, "immature": 0}, "test": {"mature": 0, "immature": 1}})

    def test_reject_naive_timestamp(self):
        with self.assertRaises(ValueError):
            maturity_mask([datetime(2026, 1, 1)], T)

    def test_reject_duplicate_grid(self):
        with self.assertRaises(ValueError):
            maturity_mask([T, T], T + timedelta(days=30))

    def test_reject_invalid_horizon(self):
        with self.assertRaises(ValueError):
            maturity_mask([T], T, True)

    def test_reject_fold_length_mismatch(self):
        with self.assertRaises(ValueError):
            fold_maturity_counts([T], [], T)

    def test_offset_normalization(self):
        plus2 = timezone(timedelta(hours=2))
        local = T.astimezone(plus2)
        self.assertEqual(maturity_mask([local], T + timedelta(days=14)), [True])


if __name__ == "__main__":
    unittest.main()
