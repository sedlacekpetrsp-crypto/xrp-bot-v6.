import unittest
from research.k11_cost_floor import CostAssumptions, round_trip_cost, feasibility_gate


class TestCostFloor(unittest.TestCase):
    def test_default_round_trip(self):
        self.assertAlmostEqual(round_trip_cost(CostAssumptions()), 0.0023)

    def test_sensitivity(self):
        self.assertAlmostEqual(round_trip_cost(CostAssumptions(), 3), 0.0069)

    def test_funding_and_adverse_selection(self):
        a = CostAssumptions(funding_round_trip=.0001, adverse_selection_round_trip=.0003)
        self.assertAlmostEqual(round_trip_cost(a), .0027)

    def test_missing_edge_blocks(self):
        self.assertEqual(feasibility_gate(None, CostAssumptions())["verdict"], "DATA_BLOCKED")

    def test_insufficient_upper_bound(self):
        self.assertEqual(feasibility_gate(.001, CostAssumptions())["verdict"], "COST_NO_GO")

    def test_equal_bound_no_go(self):
        self.assertEqual(feasibility_gate(.0023, CostAssumptions())["verdict"], "COST_NO_GO")

    def test_large_bound_not_approval(self):
        self.assertEqual(feasibility_gate(.01, CostAssumptions())["verdict"], "NOT_DISPROVEN")

    def test_bad_inputs(self):
        for bad in (-1, float("nan"), float("inf"), True):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    feasibility_gate(bad, CostAssumptions())
                with self.assertRaises(ValueError):
                    CostAssumptions(fee_per_side=bad)

    def test_multiplier_rejects_zero(self):
        with self.assertRaises(ValueError):
            round_trip_cost(CostAssumptions(), 0)

    def test_multiplier_rejects_nan(self):
        with self.assertRaises(ValueError):
            round_trip_cost(CostAssumptions(), float("nan"))


if __name__ == "__main__":
    unittest.main()
