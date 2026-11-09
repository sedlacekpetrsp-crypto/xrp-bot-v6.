"""Synthetic QA: calibration edge cases shared by both XRP radars.

No price data, model fitting, historical replay, or performance backtest.
"""
import math
import unittest

from research.top_risk_radar_v1.calibration import calibration_metrics


class CalibrationBoundaryContractTests(unittest.TestCase):
    def test_empty_sample_is_not_validation(self):
        result = calibration_metrics([])
        self.assertEqual((result["status"], result["n"]), ("insufficient_data", 0))
        self.assertIsNone(result["brier"])
        self.assertIsNone(result["log_loss"])
        self.assertTrue(all(b["observed_rate"] is None for b in result["bins"]))

    def test_exact_bin_boundaries_and_probability_one(self):
        result = calibration_metrics([(0.0, False), (0.2, True), (1.0, True)], bins=5)
        self.assertEqual([b["n"] for b in result["bins"]], [1, 1, 0, 0, 1])
        self.assertEqual(result["bins"][1]["lower"], 0.2)
        self.assertEqual(result["bins"][-1]["upper"], 1.0)

    def test_brier_uses_unclipped_extreme_probabilities(self):
        result = calibration_metrics([(0.0, True), (1.0, False)], bins=2)
        self.assertEqual(result["brier"], 1.0)
        self.assertTrue(math.isfinite(result["log_loss"]))
        self.assertGreater(result["log_loss"], 30.0)

    def test_reject_unknown_and_non_boolean_labels(self):
        for bad in (None, 0, 1, "True", 0.0):
            with self.subTest(label=bad), self.assertRaises(TypeError):
                calibration_metrics([(0.5, bad)])

    def test_reject_nonfinite_and_non_numeric_probabilities(self):
        for bad in (float("nan"), float("inf"), -float("inf"), -0.01, 1.01, True, None, "0.5"):
            with self.subTest(probability=bad), self.assertRaises(ValueError):
                calibration_metrics([(bad, True)])

    def test_reject_invalid_bin_count(self):
        for bad in (1, 101, True, 2.5, "10"):
            with self.subTest(bins=bad), self.assertRaises(ValueError):
                calibration_metrics([(0.5, True)], bins=bad)

    def test_permutation_invariance_of_aggregate_scores(self):
        rows = [(0.1, False), (0.8, True), (0.4, True), (0.6, False)]
        forward = calibration_metrics(rows, bins=5)
        reverse = calibration_metrics(list(reversed(rows)), bins=5)
        self.assertAlmostEqual(forward["brier"], reverse["brier"])
        self.assertAlmostEqual(forward["log_loss"], reverse["log_loss"])
        self.assertEqual([b["n"] for b in forward["bins"]],
                         [b["n"] for b in reverse["bins"]])


if __name__ == "__main__":
    unittest.main()
