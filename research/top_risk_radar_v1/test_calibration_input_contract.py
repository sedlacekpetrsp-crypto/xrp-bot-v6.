"""Synthetic edge-case checks for calibration diagnostics. No market-data backtest."""
import unittest

from research.top_risk_radar_v1.calibration import calibration_metrics


class CalibrationInputContract(unittest.TestCase):
    def test_empty_set_has_no_invented_metrics(self):
        result = calibration_metrics([])
        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(result["n"], 0)
        for name in ("event_rate", "brier", "log_loss"):
            self.assertIsNone(result[name])
        self.assertEqual(sum(b["n"] for b in result["bins"]), 0)

    def test_invalid_bins_rejected(self):
        for bins in (True, False, 0, 1, 101, 2.0, "10", None):
            with self.subTest(bins=bins):
                with self.assertRaises(ValueError):
                    calibration_metrics([], bins=bins)

    def test_invalid_probabilities_rejected(self):
        for p in (True, False, -0.001, 1.001, float("nan"),
                  float("inf"), -float("inf"), None, "0.5"):
            with self.subTest(probability=p):
                with self.assertRaises(ValueError):
                    calibration_metrics([(p, True)])

    def test_immature_or_non_boolean_labels_rejected(self):
        for label in (None, 0, 1, "true", 0.0, 1.0):
            with self.subTest(label=label):
                with self.assertRaises(TypeError):
                    calibration_metrics([(0.5, label)])

    def test_boundary_assignment_is_half_open_except_last(self):
        result = calibration_metrics(
            [(0.0, False), (0.25, False), (0.5, True),
             (0.75, True), (1.0, True)], bins=4)
        self.assertEqual([b["n"] for b in result["bins"]], [1, 1, 1, 2])
        self.assertEqual(result["status"], "diagnostic_only")

    def test_all_positive_and_all_negative_are_finite(self):
        for label in (True, False):
            with self.subTest(label=label):
                result = calibration_metrics([(0.5, label)] * 4)
                self.assertEqual(result["event_rate"], float(label))
                self.assertAlmostEqual(result["brier"], 0.25)
                self.assertAlmostEqual(result["log_loss"], 0.6931471805599453)


if __name__ == "__main__":
    unittest.main()
