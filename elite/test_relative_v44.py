import math
import unittest
from elite.relative_v44 import relative_scores, rule, decisions

class RelativeTests(unittest.TestCase):
    def test_thresholds_and_market_filter(self):
        self.assertGreater(rule(-2.1,-1.9,1,True,'v44').stop_distance,0)
        self.assertEqual(rule(-2.1,-1.9,1,False,'v44').stop_distance,0)
        self.assertEqual(rule(-2.1,.1,1,True,'v44').stop_distance,0)
        self.assertTrue(rule(-.1,0,1,True,'v44').exit)
        self.assertGreater(rule(1.9,2.1,1,True,'v45').stop_distance,0)
        self.assertEqual(rule(2.1,2.2,1,True,'v45').stop_distance,0)
        self.assertTrue(rule(2,.4,1,True,'v45').exit)
        self.assertEqual(rule(1,3,1,True,'v45').max_bars,2016)

    def test_current_is_not_in_fit_and_constant_is_guarded(self):
        hist=[-1.,1.]*84
        self.assertEqual(relative_scores(hist+[3.],168),(1.,3.))
        self.assertEqual(relative_scores(hist+[30.],168),(1.,30.))
        self.assertIsNone(relative_scores([1.]*169,168))

    def test_scale_invariant_and_causal(self):
        x=[];b=[]
        for i in range(205*12+7):
            p=100+math.sin(i/71)+i/1000
            q=1000+math.cos(i/139)*10+i/100
            x.append((i*300000,p,p+1,p-1,p))
            b.append((i*300000,q,q+1,q-1,q))
        scaled=[(r[0],*(v*100 for v in r[1:])) for r in b]
        for name in ('v44','v45'):
            full=decisions(x,b,name)
            self.assertEqual(full,decisions(x,scaled,name))
            prefix=decisions(x[:203*12+3],b[:203*12+3],name)
            self.assertEqual(prefix,{i:d for i,d in full.items() if i<203*12+3})
            self.assertTrue(all((i+1)%12==0 for i in full))
        with self.assertRaises(ValueError):decisions(x,b[:-1],'v44')
