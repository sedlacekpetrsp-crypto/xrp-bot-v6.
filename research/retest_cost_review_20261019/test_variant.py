import unittest
from research.candle_validation_20261019.engine import open_position,pnl
from research.retest_cost_review_20261019.variant import cost_target
class CostTargetTests(unittest.TestCase):
 def test_net_reward_and_unchanged_risk(self):
  p=dict(stop_atr=1.5,stop_multiplier=1.15,gross_reward_multiple=2,notional=1000,fee_per_side=.00095)
  for side in (-1,1):
   for slip in (.0002,.0004):
    old=open_position(side,2,.01,p,slip);new=cost_target(side,2,.01,p,slip)
    self.assertEqual(old['qty'],new['qty']);self.assertEqual(old['stop'],new['stop'])
    self.assertGreater(side*(new['target']-old['target']),0)
    self.assertAlmostEqual(pnl(new,new['target'],p['fee_per_side'],slip)[0],.03*new['qty'],places=10)
