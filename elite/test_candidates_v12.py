import unittest
from elite.candidates_v12 import candidate_decision,decisions,simple_rsi
from elite.candidates_v8 import candidate_decision as old_decision

class V12Tests(unittest.TestCase):
    def test_rsi_edges(self):
        self.assertEqual(simple_rsi([1]*15),50)
        self.assertEqual(simple_rsi(list(range(1,16))),100)
        self.assertEqual(simple_rsi(list(range(16,1,-1))),0)
    def test_v12_same_signal_different_horizon(self):
        bars=[(i,100,101,99,100+(i%2)*.1) for i in range(250)]
        bars[-2]=(248,100,100,85,86);bars[-1]=(249,86,95,86,94)
        old=old_decision(bars,249,'v8');new=candidate_decision(bars,249,'v12')
        self.assertGreater(new.stop_distance,0)
        self.assertEqual((old.stop_distance,old.target_distance),(new.stop_distance,new.target_distance))
        self.assertEqual(new.max_bars,144)
    def test_rsi_recovery(self):
        closes=[100.]*235+[100.-i for i in range(14)]+[95.]
        bars=[(i,c,c+1,c-1,c) for i,c in enumerate(closes)]
        self.assertGreater(candidate_decision(bars,249,'v13').stop_distance,0)
        bars[-1]=(249,85,86,84,85)
        self.assertEqual(candidate_decision(bars,249,'v13').stop_distance,0)
    def test_narrow_range_breakout(self):
        bars=[(i,100,101,99,100) for i in range(250)]
        bars[-2]=(248,100,100.1,99.9,100);bars[-1]=(249,100,102,100,101.9)
        self.assertGreater(candidate_decision(bars,249,'v14').stop_distance,0)
        bars[-1]=(249,100,102,100,100.1)
        self.assertEqual(candidate_decision(bars,249,'v14').stop_distance,0)
    def test_prefix_invariance(self):
        rows=[(i*300000,100+i*.01,101+i*.01,99+i*.01,100+i*.01) for i in range(10400)]
        cut=10001
        for n in ('v12','v13','v14'):
            self.assertEqual(decisions(rows[:cut],n),{i:s for i,s in decisions(rows,n).items() if i<cut})
    def test_flat(self):
        bars=[(i,100,100,100,100) for i in range(250)]
        for n in ('v12','v13','v14'):self.assertEqual(candidate_decision(bars,249,n).stop_distance,0)
