"""Regression tests for arithmetic overflow in diagnostic-only power screen."""
import unittest
from research.episode_power_preflight import PowerScreen


class DerivedFiniteTests(unittest.TestCase):
    def test_cost_addition_overflow_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Non-finite derived"):
            PowerScreen(100, 0.1, 1e308, 1e308, 1).evaluate()

    def test_mde_overflow_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Non-finite derived"):
            PowerScreen(2, 1e308, 0.001, 0.001, 1, multiplicity=100).evaluate()

    def test_regular_finite_case(self):
        result = PowerScreen(100, 0.03, 0.0019, 0.0004, 2).evaluate()
        self.assertEqual(result["status"], "DIAGNOSTIC_ONLY")
        self.assertGreater(result["required_gross_return_for_gate"], 0)


if __name__ == "__main__":
    unittest.main()
