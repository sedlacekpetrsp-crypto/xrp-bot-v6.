import unittest
from decimal import Decimal
from research.cost_feasibility_gate import minimum_gross_move, classify_gross_target

class CostFeasibilityTests(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(minimum_gross_move("0", "0"), Decimal("0"))
    def test_default_above_simple_roundtrip(self):
        self.assertGreater(minimum_gross_move(), Decimal("0.0023"))
    def test_default_below_three_tenths_percent(self):
        self.assertLess(minimum_gross_move(), Decimal("0.003"))
    def test_cost_floor(self):
        self.assertEqual(classify_gross_target("0.002"), "BELOW_COST_FLOOR")
    def test_not_profit_claim(self):
        self.assertEqual(classify_gross_target("0.01"), "ABOVE_COST_FLOOR_UNVALIDATED")
    def test_reject_negative(self):
        with self.assertRaises(ValueError):
            minimum_gross_move("-0.1")
    def test_reject_nan(self):
        with self.assertRaises(ValueError):
            minimum_gross_move("NaN")
    def test_reject_combined(self):
        with self.assertRaises(ValueError):
            minimum_gross_move("0.6", "0.5")
    def test_buffer(self):
        self.assertGreater(minimum_gross_move(extra_buffer="0.001"), minimum_gross_move())

if __name__ == "__main__":
    unittest.main()
