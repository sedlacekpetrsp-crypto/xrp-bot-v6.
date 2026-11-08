"""Synthetic scoring-rule invariants; no market data or performance backtest.

These tests verify that the calibration diagnostics reward accurate probabilities
and do not accidentally interpret certainty, event frequency, or class balance
as predictive evidence.
"""
import math
import unittest

from research.top_risk_radar_v1.calibration import calibration_metrics


class ProperScoringInvariants(unittest.TestCase):
    def test_improved_probability_has_lower_brier_and_log_loss(self):
        labels = [True, False, True, False]
        accurate = calibration_metrics([(0.9 if y else 0.1, y) for y in labels])
        weak = calibration_metrics([(0.6 if y else 0.4, y) for y in labels])
        for metric in ("brier", "log_loss"):
            self.assertLess(accurate[metric], weak[metric])

    def test_overconfident_wrong_forecast_is_penalized(self):
        wrong = calibration_metrics([(0.99, False), (0.01, True)])
        uncertain = calibration_metrics([(0.5, False), (0.5, True)])
        for metric in ("brier", "log_loss"):
            self.assertGreater(wrong[metric], uncertain[metric])

    def test_constant_climatology_brier_matches_event_variance(self):
        labels = [True, False, False, False]
        prevalence = sum(labels) / len(labels)
        result = calibration_metrics([(prevalence, y) for y in labels])
        self.assertAlmostEqual(result["brier"], prevalence * (1 - prevalence))
        self.assertAlmostEqual(result["event_rate"], prevalence)

    def test_brier_is_invariant_to_permutation(self):
        rows = [(0.05, False), (0.75, True), (0.3, False), (0.9, True)]
        original = calibration_metrics(rows, bins=5)
        reversed_result = calibration_metrics(list(reversed(rows)), bins=5)
        for metric in ("brier", "log_loss", "event_rate"):
            self.assertAlmostEqual(original[metric], reversed_result[metric])
        self.assertEqual([b["n"] for b in original["bins"]],
                         [b["n"] for b in reversed_result["bins"]])

    def test_extreme_probabilities_have_finite_log_loss(self):
        result = calibration_metrics([(0.0, True), (1.0, False)])
        self.assertTrue(math.isfinite(result["log_loss"]))
        self.assertAlmostEqual(result["brier"], 1.0)
        self.assertGreater(result["log_loss"], 30.0)

    def test_single_observation_is_diagnostic_not_validation(self):
        result = calibration_metrics([(0.9, True)])
        self.assertEqual(result["status"], "diagnostic_only")
        self.assertEqual(result["n"], 1)


if __name__ == "__main__":
    unittest.main()
