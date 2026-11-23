import unittest
from research.g1_precision_denominator_preflight import (
    wilson_lower, minimum_successes, preflight_denominators
)


class TestPreflight(unittest.TestCase):
    def test_all_successes_not_always_enough(self):
        self.assertIsNone(minimum_successes(3, 0.6))

    def test_recall_and_precision_have_distinct_denominators(self):
        result = preflight_denominators(21, 8)
        self.assertEqual(result["positive_episode_count"], 21)
        self.assertEqual(result["alert_episode_budget"], 8)
        self.assertNotEqual(result["minimum_recall_hits"], result["minimum_precision_true_alerts"])

    def test_zero_trials_rejected(self):
        with self.assertRaises(ValueError):
            minimum_successes(0, 0.6)

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            wilson_lower(True, 5)

    def test_invalid_successes_rejected(self):
        with self.assertRaises(ValueError):
            wilson_lower(6, 5)

    def test_nonfinite_threshold_rejected(self):
        with self.assertRaises(ValueError):
            minimum_successes(10, float("nan"))

    def test_monotonic_lower_bound(self):
        self.assertLess(wilson_lower(4, 10), wilson_lower(5, 10))


if __name__ == "__main__":
    unittest.main()
