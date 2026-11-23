"""Review tests (Claude, dialog 0462) for aba544c/0d6e42e. Synthetic only, no market data."""
import unittest
from decimal import Decimal
import pytest
from research.cost_feasibility_gate import minimum_gross_move, classify_gross_target


class ReviewCostFeasibility(unittest.TestCase):
    def test_breakeven_identity(self):
        # exit cash == entry cash exactly at the hurdle (long roundtrip)
        fee, slip = Decimal("0.00095"), Decimal("0.0002")
        m = minimum_gross_move()
        side = fee + slip
        self.assertAlmostEqual(float((1 + m) * (1 - side) - (1 + side)), 0.0, places=25)

    def test_close_to_linear_k11_cost(self):
        # k11_cost_floor x1 = 2*(fee+slip) = 0.0023; compounding makes hurdle slightly higher
        m = minimum_gross_move()
        self.assertTrue(Decimal("0.0023") < m < Decimal("0.00231"))

    @pytest.mark.xfail(strict=True, reason="0462 M1: gate uses 1x break-even, framework binding filter is >= 3x cost")
    def test_three_x_filter_applied(self):
        # 0.5 % gross target is above 1x (0.23 %) but below 3x (~0.69 %) -> must not pass
        self.assertEqual(classify_gross_target("0.005"), "BELOW_COST_FLOOR")

    @pytest.mark.xfail(strict=True, reason="0462 m2: target >= 100 % move rejected as 'cost rate'")
    def test_large_target_allowed(self):
        self.assertEqual(classify_gross_target("1.5"), "ABOVE_COST_FLOOR_UNVALIDATED")

    def test_buffer_is_scaled_not_additive(self):
        # 0462 m3: extra_buffer enters the numerator -> hurdle rises by buffer/(1-side), not by buffer
        d = minimum_gross_move(extra_buffer="0.001") - minimum_gross_move()
        self.assertGreater(d, Decimal("0.001"))


if __name__ == "__main__":
    unittest.main()
