import unittest
from risk import drawdown_bounds


class RiskTests(unittest.TestCase):
    def test_hidden_intratrade_loss(self):
        bars={0:[0,100,110,80,100],60:[60000,100,100,100,100]}
        r=drawdown_bounds([dict(entry_ts=0,exit_ts=60)],bars,0,0)
        self.assertAlmostEqual(r['final_net_return'],0)
        self.assertAlmostEqual(r['max_drawdown_lower_bound'],.2)
        self.assertAlmostEqual(r['max_drawdown_upper_bound'],1-80/110)

    def test_missing_candle_rejected(self):
        with self.assertRaises(ValueError):
            drawdown_bounds([dict(entry_ts=0,exit_ts=120)],{})

    def test_flat_price_costs(self):
        bars={0:[0,100,100,100,100],60:[60000,100,100,100,100]}
        r=drawdown_bounds([dict(entry_ts=0,exit_ts=60)],bars)
        self.assertAlmostEqual(r['max_drawdown_lower_bound'],-r['final_net_return'])
        self.assertAlmostEqual(r['max_drawdown_upper_bound'],r['max_drawdown_lower_bound'])
