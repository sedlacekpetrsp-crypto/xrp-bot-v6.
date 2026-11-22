"""Synthetic tests only: never historical performance."""
import unittest
from research.k11_cost_floor import CostAssumptions
from research.k11_cost_sensitivity import BoundEvidence, assess_sensitivity


class TestK11Sensitivity(unittest.TestCase):
    def setUp(self):
        self.cost = CostAssumptions()
    def evidence(self, bound, source="independent-study", timestamp="2026-01-01T00:00:00Z"):
        return BoundEvidence(bound, source, timestamp)
    def test_missing_bound_blocks(self):
        self.assertEqual(assess_sensitivity(self.evidence(None), self.cost)["verdict"], "DATA_BLOCKED")
    def test_missing_source_blocks(self):
        self.assertEqual(assess_sensitivity(self.evidence(.01, ""), self.cost)["verdict"], "DATA_BLOCKED")
    def test_missing_timestamp_blocks(self):
        self.assertEqual(assess_sensitivity(self.evidence(.01, timestamp=None), self.cost)["verdict"], "DATA_BLOCKED")
    def test_cost_floor(self):
        self.assertAlmostEqual(assess_sensitivity(self.evidence(.01), self.cost)["costs"]["x1"], .0023)
    def test_sensitivity_monotone(self):
        v = assess_sensitivity(self.evidence(.004), self.cost)["costs"]
        self.assertLess(v["x1"], v["x2"])
        self.assertLess(v["x2"], v["x3"])
    def test_boundary_no_go(self):
        self.assertEqual(assess_sensitivity(self.evidence(.0023), self.cost)["verdict"], "COST_NO_GO")
    def test_high_bound_not_approval(self):
        v = assess_sensitivity(self.evidence(.01), self.cost)
        self.assertEqual(v["verdict"], "NOT_DISPROVEN")
        self.assertFalse(v["pit_verified"])
    def test_middle_sensitivity_failure(self):
        v = assess_sensitivity(self.evidence(.003), self.cost)
        self.assertTrue(v["passes"]["x1"])
        self.assertFalse(v["passes"]["x2"])
    def test_invalid_nan(self):
        with self.assertRaises(ValueError):
            assess_sensitivity(self.evidence(float("nan")), self.cost)
    def test_boolean_invalid(self):
        with self.assertRaises(ValueError):
            assess_sensitivity(self.evidence(True), self.cost)
    def test_funding_included(self):
        v = assess_sensitivity(self.evidence(.003), CostAssumptions(funding_round_trip=.001))
        self.assertFalse(v["passes"]["x1"])


if __name__ == "__main__":
    unittest.main()
