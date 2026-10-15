import math
import unittest
from elite.regime_v46 import rule, decisions

class RegimeTests(unittest.TestCase):
    def test_trend_reclaim_and_cost_floor(self):
        self.assertGreater(rule('v46',99,101,99,100,100,1,.4,True).stop_distance,0)
        self.assertEqual(rule('v46',99,101,99,100,100,1,.2,True).stop_distance,0)
        self.assertEqual(rule('v46',99,101,99,100,100,.1,.4,True).stop_distance,0)
        self.assertTrue(rule('v46',99,101,99,100,100,1,.4,False).exit)

    def test_range_reclaim_not_just_oversold(self):
        self.assertGreater(rule('v47',99,97,95,100,100,2,.1,False).stop_distance,0)
        self.assertEqual(rule('v47',99,95,94,100,100,2,.1,False).stop_distance,0)
        self.assertEqual(rule('v47',99,97,95,100,100,2,.4,False).stop_distance,0)
        self.assertEqual(rule('v47',99,101,95,100,100,2,.1,False).stop_distance,0)
        self.assertTrue(rule('v47',99,101,95,100,100,2,.1,False).exit)

    def test_prefix_and_completed_hours(self):
        rows=[]
        for i in range(220*12+5):
            p=100+math.sin(i/17)*2+i/10000
            rows.append((i*300000,p,p+1,p-1,p))
        for name in ('v46','v47'):
            full=decisions(rows,name)
            prefix=decisions(rows[:210*12+3],name)
            self.assertEqual(prefix,{i:d for i,d in full.items() if i<210*12+3})
            self.assertTrue(all((i+1)%12==0 for i in full))
