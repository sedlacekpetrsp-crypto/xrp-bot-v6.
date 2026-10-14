import unittest
from elite.candidates_v24 import signals,decisions

class CandidateTests(unittest.TestCase):
    def bars(self,n=203):return [(i,100,101,99,100) for i in range(n)]
    def test_failed_breakdown_reclaim(self):
        b=self.bars();b[200]=(200,99,101,97,100.5)
        self.assertGreater(signals(b,'v24')[200].stop_distance,0)
        b[200]=(200,99,101,97,98)
        self.assertEqual(signals(b,'v24')[200].stop_distance,0)
    def test_retest_waits_and_consumes(self):
        b=self.bars();b[200]=(200,100,103,99,102);b[201]=(201,102,103,100,102);b[202]=b[201][:0]+(202,102,103,100,102)
        s=signals(b,'v25')
        self.assertEqual(s[200].stop_distance,0)
        self.assertGreater(s[201].stop_distance,0)
        self.assertEqual(s[202].stop_distance,0)
    def test_expired_setup(self):
        b=self.bars(227);b[200]=(200,100,103,99,102)
        for k in range(201,226):b[k]=(k,102,103,101.5,102)
        b[226]=(226,102,103,100,102)
        self.assertEqual(signals(b,'v25')[226].stop_distance,0)
    def test_invalidated_setup(self):
        b=self.bars();b[200]=(200,100,103,99,102);b[201]=(201,100,101,97,98);b[202]=(202,102,103,100,102)
        self.assertEqual(signals(b,'v25')[202].stop_distance,0)
    def test_future_cannot_change_past(self):
        rows=[(i*300000,100,101,99,100) for i in range(10100)]
        changed=rows[:10001]+[(t,o*2,h*2,l*2,c*2) for t,o,h,l,c in rows[10001:]]
        for n in ('v24','v25'):
            self.assertEqual(decisions(rows[:10001],n),{i:s for i,s in decisions(changed,n).items() if i<10001})
