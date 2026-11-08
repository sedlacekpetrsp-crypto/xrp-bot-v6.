"""Unit tests for descriptive (non-predictive) prevalence baseline."""
import unittest
from datetime import datetime, timedelta, timezone

from research.top_risk_radar_v1.prevalence_baseline import (
    Observation, historical_prevalence,
)

T = datetime(2025, 1, 1, tzinfo=timezone.utc)


class PrevalenceBaselineTests(unittest.TestCase):
    def test_no_future_labels(self):
        rows = [
            Observation(T - timedelta(days=40), True, False),
            Observation(T - timedelta(days=5), False, True),
        ]
        self.assertEqual(historical_prevalence(rows, T, horizon_days=30, target="growth")["rate"], 1)

    def test_unknown_not_negative(self):
        rows = [Observation(T - timedelta(days=40), None, None)]
        self.assertEqual(historical_prevalence(rows, T, horizon_days=30, target="growth")["status"], "insufficient_train")

    def test_valid_rate(self):
        rows = [
            Observation(T - timedelta(days=40), True, False),
            Observation(T - timedelta(days=50), False, True),
        ]
        self.assertEqual(historical_prevalence(rows, T, horizon_days=14, target="downside")["rate"], 0.5)

    def test_invalid_target(self):
        with self.assertRaises(ValueError):
            historical_prevalence([], T, horizon_days=14, target="price")

    def test_naive_test_start_rejected(self):
        with self.assertRaises(ValueError):
            historical_prevalence([], T.replace(tzinfo=None), horizon_days=14, target="downside")

    def test_naive_train_timestamp_rejected_even_if_label_unknown(self):
        rows = [Observation((T - timedelta(days=40)).replace(tzinfo=None), None, None)]
        with self.assertRaises(ValueError):
            historical_prevalence(rows, T, horizon_days=14, target="downside")

    def test_nonboolean_label_rejected(self):
        rows = [Observation(T - timedelta(days=40), 1, False)]
        with self.assertRaises(TypeError):
            historical_prevalence(rows, T, horizon_days=14, target="growth")

    def test_horizon_maturity_exact_boundary(self):
        rows = [
            Observation(T - timedelta(days=14), None, True),
            Observation(T - timedelta(days=14) + timedelta(microseconds=1), None, False),
        ]
        result = historical_prevalence(rows, T, horizon_days=14, target="downside")
        self.assertEqual((result["n"], result["rate"]), (1, 1))

    def test_offset_aware_equivalence(self):
        plus_one = timezone(timedelta(hours=1))
        rows = [Observation((T - timedelta(days=14)).astimezone(plus_one), False, True)]
        result = historical_prevalence(rows, T, horizon_days=14, target="downside")
        self.assertEqual(result["rate"], 1)

    def test_future_training_row_excluded(self):
        rows = [Observation(T + timedelta(days=1), True, True)]
        self.assertEqual(historical_prevalence(rows, T, horizon_days=14, target="growth")["n"], 0)

    def test_invalid_horizon_type(self):
        for horizon in (0, -1, True, 1.5):
            with self.subTest(horizon=horizon), self.assertRaises(ValueError):
                historical_prevalence([], T, horizon_days=horizon, target="growth")


if __name__ == "__main__":
    unittest.main()
