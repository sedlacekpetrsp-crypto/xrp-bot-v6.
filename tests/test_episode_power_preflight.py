import math
import unittest
from research.episode_power_preflight import PowerScreen

class TestPowerScreen(unittest.TestCase):
    def screen(self, **kw):
        return PowerScreen(**({"n_episodes": 25, "sigma_return": .02,
                               "roundtrip_fee": .0019,
                               "roundtrip_slippage": .0004} | kw))
    def test_known_mde(self):
        r = self.screen().evaluate()
        self.assertAlmostEqual(r["minimum_detectable_gross_return"], .0112)
        self.assertAlmostEqual(r["required_gross_return_for_net_detection"], .0135)
    def test_more_episodes_reduce_mde(self):
        self.assertLess(self.screen(n_episodes=100).evaluate()["minimum_detectable_gross_return"],
                        self.screen().evaluate()["minimum_detectable_gross_return"])
    def test_costs_increase_required_gross(self):
        self.assertGreater(self.screen(roundtrip_fee=.005).evaluate()["required_gross_return_for_net_detection"],
                           self.screen().evaluate()["required_gross_return_for_net_detection"])
    def test_reject_bad_inputs(self):
        for changes in ({"n_episodes": 1}, {"n_episodes": True},
                        {"sigma_return": 0}, {"sigma_return": math.nan},
                        {"roundtrip_fee": -.1}, {"roundtrip_slippage": math.inf},
                        {"multiplicity": 2}, {"multiplicity": True}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.screen(**changes).evaluate()
    def test_not_a_profitability_verdict(self):
        self.assertEqual(self.screen().evaluate()["status"], "DIAGNOSTIC_ONLY")

if __name__ == "__main__":
    unittest.main()
