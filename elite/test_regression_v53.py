import math
import unittest
from elite.regression_v53 import trend, signals


def bars(prices):
    return [(48*i+47,p,p*1.005,p*.995,p) for i,p in enumerate(prices)]


class RegressionTests(unittest.TestCase):
    def test_known_log_slope_and_price_scale_invariance(self):
        p = [math.exp(.01*i+.001*(i%2)) for i in range(42)]
        slope, score = trend(p)
        other = trend([x*100 for x in p])
        self.assertAlmostEqual(slope,.01,places=5)
        self.assertAlmostEqual(slope,other[0],places=12)
        self.assertAlmostEqual(score,other[1],places=7)

    def test_flat_and_falling_do_not_buy(self):
        for p in ([100.]*80,[100*math.exp(-.002*i) for i in range(80)]):
            out = signals(bars(p))
            self.assertFalse(any(d.stop_distance for d in out.values()))
            self.assertTrue(all(d.exit for d in out.values()))

    def test_sustained_rise_one_attempt(self):
        out = signals(bars([100*math.exp(.002*i) for i in range(80)]))
        buys = [d for d in out.values() if d.stop_distance]
        self.assertEqual(len(buys),1)
        self.assertEqual(buys[0].target_distance,2*buys[0].stop_distance)
        self.assertEqual(buys[0].max_bars,2016)

    def test_prefixes_and_rearm_after_weak_trend(self):
        p=[100.]*50+[100*math.exp(.004*i) for i in range(50)]+[100.]*60+[100*math.exp(.004*i) for i in range(50)]
        b=bars(p); full=signals(b)
        self.assertGreaterEqual(sum(d.stop_distance>0 for d in full.values()),2)
        for n in (42,65,100,155,190):
            self.assertEqual(signals(b[:n]),{i:d for i,d in full.items() if i<=b[n-1][0]})

    def test_invalid_prices(self):
        for p in ([1,2], [1,0,2], [1,float('nan'),2]):
            with self.assertRaises(ValueError): trend(p)
