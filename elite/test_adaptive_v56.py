import unittest
from elite.adaptive_v56 import adaptive_average,signals


def bars(close):return [(48*k+47,c,c+1,c-1,c) for k,c in enumerate(close)]


class AdaptiveTests(unittest.TestCase):
    def test_flat_seed_and_average(self):
        a=adaptive_average([100.]*30)
        self.assertEqual(a[:9],[None]*9)
        self.assertEqual(a[9:],[100.]*21)

    def test_straight_path_known_update(self):
        a=adaptive_average(list(range(1,22)))
        self.assertEqual(a[9],5.5)
        self.assertAlmostEqual(a[10],5.5+(4/9)*(11-5.5))

    def test_prefix_causality(self):
        p=[100+.2*k+(k%7)*.15 for k in range(120)]
        full=signals(bars(p));a=adaptive_average(p)
        for n in (10,49,64,99):
            self.assertEqual(adaptive_average(p[:n]),a[:n])
            self.assertEqual(signals(bars(p[:n])),{i:d for i,d in full.items() if i<=48*n-1})

    def test_declining_and_flat_no_buys(self):
        for p in ([100.]*100,[120-.2*k for k in range(100)]):
            self.assertFalse(any(d.stop_distance for d in signals(bars(p)).values()))

    def test_reclaim_and_two_close_exit(self):
        p=[100+.2*k for k in range(70)]+[112.,115.,110.,109.]
        out=signals(bars(p))
        self.assertGreater(out[48*71+47].stop_distance,0)
        self.assertFalse(out[48*72+47].exit)
        self.assertTrue(out[48*73+47].exit)
        self.assertEqual(out[48*71+47].target_distance,0)

    def test_invalid_close_rejected(self):
        for c in (0.,float('nan'),float('inf')):
            with self.assertRaises(ValueError):adaptive_average([100.]*10+[c])
