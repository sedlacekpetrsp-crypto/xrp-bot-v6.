"""Synthetic input validation tests; no market data or performance evaluation."""
import unittest
from research.episode_power_preflight import PowerScreen


class PowerInputGuardTests(unittest.TestCase):
    def base(self, **changes):
        values = dict(n_episodes=80, sigma_return=0.02,
                      roundtrip_fee=0.0019, roundtrip_slippage=0.0004,
                      design_effect=2.0)
        values.update(changes)
        return PowerScreen(**values)

    def test_rejects_power_below_half(self):
        for power in (0.0, 0.2, 0.49, 0.5):
            with self.subTest(power=power), self.assertRaises(ValueError):
                self.base(power=power).evaluate()

    def test_rejects_power_one(self):
        with self.assertRaises(ValueError):
            self.base(power=1.0).evaluate()

    def test_accepts_preregistered_power_above_half(self):
        result = self.base(power=0.8).evaluate()
        self.assertEqual(result["status"], "DIAGNOSTIC_ONLY")
        self.assertEqual(result["power_assumption"], 0.8)
        self.assertGreater(result["required_gross_return_for_gate"], 0)

    def test_mde_increases_with_power(self):
        low = self.base(power=0.6).evaluate()
        high = self.base(power=0.9).evaluate()
        self.assertGreater(high["minimum_detectable_gross_return"],
                           low["minimum_detectable_gross_return"])


if __name__ == "__main__":
    unittest.main()
