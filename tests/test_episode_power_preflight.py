import math
import unittest
from research.episode_power_preflight import PowerScreen


class TestPowerScreen(unittest.TestCase):
    def screen(self, **kw):
        return PowerScreen(**({"n_episodes": 25, "sigma_return": .02,
                               "roundtrip_fee": .0019,
                               "roundtrip_slippage": .0004,
                               "design_effect": 1.0} | kw))

    def test_known_mde(self):
        r = self.screen().evaluate()
        self.assertAlmostEqual(r["minimum_detectable_gross_return"], .011206, places=4)
        self.assertAlmostEqual(r["required_gross_return_for_net_detection"], .013506, places=4)

    def test_more_episodes_reduce_mde(self):
        self.assertLess(self.screen(n_episodes=100).evaluate()["minimum_detectable_gross_return"],
                        self.screen().evaluate()["minimum_detectable_gross_return"])

    def test_costs_increase_required_gross(self):
        self.assertGreater(self.screen(roundtrip_fee=.005).evaluate()["required_gross_return_for_net_detection"],
                           self.screen().evaluate()["required_gross_return_for_net_detection"])

    def test_design_effect_inflates_mde(self):
        a = self.screen().evaluate()
        b = self.screen(design_effect=4).evaluate()
        self.assertAlmostEqual(b["n_effective"], 6.25)
        self.assertAlmostEqual(b["minimum_detectable_gross_return"], 2 * a["minimum_detectable_gross_return"])

    def test_multiplicity_adjustment(self):
        self.assertGreater(self.screen(multiplicity=10).evaluate()["minimum_detectable_gross_return"],
                           self.screen().evaluate()["minimum_detectable_gross_return"])

    def test_three_times_cost_floor(self):
        r = self.screen(n_episodes=1000000).evaluate()
        self.assertAlmostEqual(r["required_gross_return_for_gate"], 3 * r["roundtrip_cost"])

    def test_small_sample_warning(self):
        self.assertTrue(self.screen().evaluate()["small_sample_warning"])
        self.assertFalse(self.screen(n_episodes=100).evaluate()["small_sample_warning"])

    def test_design_effect_is_mandatory(self):
        with self.assertRaises(TypeError):
            PowerScreen(n_episodes=25, sigma_return=.02, roundtrip_fee=.0019,
                        roundtrip_slippage=.0004)

    def test_reject_bad_inputs(self):
        for changes in ({"n_episodes": 1}, {"n_episodes": True},
                        {"sigma_return": 0}, {"sigma_return": math.nan},
                        {"roundtrip_fee": -.1}, {"roundtrip_slippage": math.inf},
                        {"multiplicity": True}, {"design_effect": .9},
                        {"design_effect": math.nan}, {"design_effect": 100},
                        {"alpha": 0}, {"power": 1}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.screen(**changes).evaluate()

    def test_not_a_profitability_verdict(self):
        self.assertEqual(self.screen().evaluate()["status"], "DIAGNOSTIC_ONLY")
        self.assertNotIn("minimum_detectable_net_return", self.screen().evaluate())


if __name__ == "__main__":
    unittest.main()
