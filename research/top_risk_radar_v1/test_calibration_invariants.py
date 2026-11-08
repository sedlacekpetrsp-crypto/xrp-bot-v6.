"""Additional deterministic QA invariants for calibration; synthetic labels only.

No market data, predictive evaluation, model fitting, or performance backtest.
"""
import math
import unittest

from research.top_risk_radar_v1.calibration import calibration_metrics


class CalibrationInvariants(unittest.TestCase):
    def test_order_independence(self):
        rows = [(0.05, False), (0.25, True), (0.75, True), (0.95, False)]
        forward = calibration_metrics(rows, bins=4)
        reverse = calibration_metrics(list(reversed(rows)), bins=4)
        self.assertAlmostEqual(forward["brier"], reverse["brier"])
        self.assertAlmostEqual(forward["log_loss"], reverse["log_loss"])
        self.assertEqual([b["n"] for b in forward["bins"]],
                         [b["n"] for b in reverse["bins"]])

    def test_bin_conservation(self):
        rows = [(0.0, False), (0.2, True), (0.5, False),
                (0.8, True), (1.0, True)]
        result = calibration_metrics(rows, bins=5)
        self.assertEqual(result["n"], len(rows))
        self.assertEqual(sum(b["n"] for b in result["bins"]), len(rows))
        self.assertEqual(result["event_rate"], 3 / 5)
        self.assertEqual(result["bins"][-1]["n"], 2)

    def test_empty_bin_has_no_fabricated_rate(self):
        result = calibration_metrics([(0.0, False)], bins=5)
        for item in result["bins"][1:]:
            self.assertEqual(item["n"], 0)
            self.assertIsNone(item["mean_prediction"])
            self.assertIsNone(item["observed_rate"])

    def test_extreme_probabilities_finite_log_loss(self):
        result = calibration_metrics([(0.0, True), (1.0, False)])
        self.assertTrue(math.isfinite(result["log_loss"]))
        self.assertGreater(result["log_loss"], 30)
        self.assertEqual(result["brier"], 1.0)

    def test_constant_baseline_brier_identity(self):
        labels = [True, False, False, True, False]
        prevalence = sum(labels) / len(labels)
        result = calibration_metrics([(prevalence, y) for y in labels])
        self.assertAlmostEqual(result["brier"], prevalence * (1 - prevalence))


if __name__ == "__main__":
    unittest.main()
