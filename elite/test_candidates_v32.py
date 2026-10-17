import unittest
from elite.candidates_v32 import decisions,signal,higher_trend

class IntradayTests(unittest.TestCase):
    def test_contraction_breakout_and_hurdle(self):
        b=[(i,100,101,99,100) for i in range(201)]
        for i in range(192,200):b[i]=(i,100,100.2,99.8,100)
        b[-1]=(200,100,102,99.8,101.5)
        self.assertGreater(signal(b,200,'v32',True).stop_distance,0)
        self.assertEqual(signal(b,200,'v32',False).stop_distance,0)
        tiny=[(i,100+(o-100)*.05,100+(h-100)*.05,100+(l-100)*.05,100+(c-100)*.05) for i,o,h,l,c in b]
        self.assertEqual(signal(tiny,200,'v32',True).stop_distance,0)
        self.assertGreater(signal(tiny,200,'v32',True,False).stop_distance,0)
    def test_rebound_requires_break_of_prior_high(self):
        b=[(i,100,101,99,100) for i in range(201)]
        b[199]=(199,100,100.5,97,98);b[200]=(200,98,102,98,101)
        self.assertGreater(signal(b,200,'v33',True).stop_distance,0)
        b[200]=(200,98,100.5,98,100.5)
        self.assertEqual(signal(b,200,'v33',True).stop_distance,0)
    def test_higher_trend_needs_history(self):
        b=[(i,100+i,101+i,99+i,100+i) for i in range(70)]
        self.assertFalse(higher_trend(b,64));self.assertTrue(higher_trend(b,65))
        self.assertFalse(higher_trend([(i,100,101,99,100) for i in range(70)],65))
    def test_incomplete_higher_candle_not_visible(self):
        r=[(i*300000,100+i*.01,101+i*.01,99+i*.01,100+i*.01) for i in range(3600)]
        cut=3501
        changed=r[:cut]+[(t,o*2,h*2,l*2,c*2) for t,o,h,l,c in r[cut:]]
        for n in ('v32','v33'):
            self.assertEqual(decisions(r[:cut],n),{i:s for i,s in decisions(changed,n).items() if i<cut})
    def test_regime_loss_signals_exit(self):
        b=[(i,100,101,99,100) for i in range(201)]
        for n in ('v32','v33'):self.assertTrue(signal(b,200,n,False).exit)
