import unittest
from elite.research_engine import Decision
from elite.cross_market_v18 import decisions,signal,align

class CrossMarketTests(unittest.TestCase):
    def rows(self,n):return [(i*300000,100+i*.01,101+i*.01,99+i*.01,100+i*.01) for i in range(n)]
    def test_timestamp_mismatch_fails(self):
        a=self.rows(100);b=[(t+300000,o,h,l,c) for t,o,h,l,c in a]
        with self.assertRaises(ValueError):align(a,b)
    def test_v18_gate_preserves_exit(self):
        flat=[(i,100,101,99,100) for i in range(250)]
        s=signal(flat,flat,249,'v18',Decision(3,exit=True))
        self.assertEqual(s.stop_distance,0);self.assertTrue(s.exit)
        rising=[(i,100+i,101+i,99+i,100+i) for i in range(250)]
        self.assertEqual(signal(flat,rising,249,'v18',Decision(3)).stop_distance,3)
    def test_flat_no_entries(self):
        flat=[(i,100,101,99,100) for i in range(250)]
        for n in ('v18','v19','v20'):
            self.assertEqual(signal(flat,flat,249,n,Decision()).stop_distance,0)
    def test_v19_trigger(self):
        x=[(i,100,101,99,100) for i in range(250)]
        b=[(i,100+i*.01,101+i*.01,99+i*.01,100+i*.01) for i in range(250)]
        x[-1]=(249,100,103,99,102)
        self.assertGreater(signal(x,b,249,'v19').stop_distance,0)
    def test_v20_trigger(self):
        x=[(i,100,101,99,100) for i in range(250)]
        b=[(i,100+i*.2,101+i*.2,99+i*.2,100+i*.2) for i in range(250)]
        for k in range(244,249):x[k]=(k,95,96,94,95)
        x[249]=(249,95,100,94,99)
        self.assertGreater(signal(x,b,249,'v20').stop_distance,0)
    def test_both_markets_prefix_invariant(self):
        x=self.rows(3000);b=self.rows(3000);cut=2501
        changed=b[:cut]+[(t,o*2,h*2,l*2,c*2) for t,o,h,l,c in b[cut:]]
        for n in ('v18','v19','v20'):
            expected=decisions(x[:cut],b[:cut],n)
            self.assertEqual(expected,{i:s for i,s in decisions(x,changed,n).items() if i<cut})
