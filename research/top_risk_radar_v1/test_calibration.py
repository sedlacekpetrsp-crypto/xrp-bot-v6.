"""Unit tests for calibration diagnostics; synthetic examples only."""
import math
import unittest
from research.top_risk_radar_v1.calibration import calibration_metrics


class CalibrationTests(unittest.TestCase):
    def test_empty(self):
        result = calibration_metrics([])
        self.assertEqual(result["status"], "insufficient_data")
        self.assertIsNone(result["brier"])
        self.assertEqual(sum(b["n"] for b in result["bins"]), 0)

    def test_perfect(self):
        result = calibration_metrics([(0.0, False), (1.0, True)])
        self.assertEqual(result["brier"], 0)
        self.assertEqual(result["event_rate"], 0.5)
        self.assertEqual(result["bins"][-1]["observed_rate"], 1.0)

    def test_known_values(self):
        result = calibration_metrics([(0.25, True), (0.75, False)], bins=2)
        self.assertAlmostEqual(result["brier"], 0.5625)
        self.assertAlmostEqual(result["log_loss"], -math.log(0.25))
        self.assertEqual([b["n"] for b in result["bins"]], [1, 1])

    def test_exact_one_in_last_bin(self):
        self.assertEqual(calibration_metrics([(1, True)], bins=10)["bins"][-1]["n"], 1)

    def test_invalid_probabilities(self):
        for p in (float("nan"), float("inf"), -0.01, 1.01, True, "0.5", None):
            with self.subTest(p=p), self.assertRaises(ValueError):
                calibration_metrics([(p, True)])

    def test_unknown_or_nonboolean_labels(self):
        for y in (None, 0, 1, "false"):
            with self.subTest(y=y), self.assertRaises(TypeError):
                calibration_metrics([(0.5, y)])

    def test_invalid_bins(self):
        for bins in (0, 1, 101, 2.5, True):
            with self.subTest(bins=bins), self.assertRaises(ValueError):
                calibration_metrics([], bins=bins)


if __name__ == "__main__":
    unittest.main()
