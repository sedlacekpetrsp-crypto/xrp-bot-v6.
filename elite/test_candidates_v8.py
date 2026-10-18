import unittest
from elite.candidates_v8 import decisions,candidate_decision,efficiency
from elite.batch_v8 import discovery_failures

class CandidateTests(unittest.TestCase):
    def test_efficiency(self):
        self.assertEqual(efficiency([1,2,3]),1)
        self.assertEqual(efficiency([1,2,1]),0)
        self.assertEqual(efficiency([1,1,1]),0)
    def test_flat_no_entries(self):
        bars=[(i,100,100,100,100) for i in range(250)]
        for n in ('v8','v9','v10','v11'):
            self.assertEqual(candidate_decision(bars,249,n).stop_distance,0)
    def test_shock_recovery(self):
        bars=[(i,100,101,99,100+(i%2)*.1) for i in range(250)]
        bars[-2]=(248,100,100,85,86);bars[-1]=(249,86,95,86,94)
        self.assertGreater(candidate_decision(bars,249,'v8').stop_distance,0)
        bars[-1]=(249,86,90,84,85)
        self.assertEqual(candidate_decision(bars,249,'v8').stop_distance,0)
    def test_prefix_invariance(self):
        rows=[(i*300000,100+i*.01,101+i*.01,99+i*.01,100+i*.01) for i in range(10400)]
        cut=10001
        for n in ('v8','v9','v10','v11'):
            prefix=decisions(rows[:cut],n)
            full=decisions(rows,n)
            self.assertEqual(prefix,{i:d for i,d in full.items() if i<cut})
            self.assertTrue(all((i+1)%(48 if n in ('v8','v10') else 12)==0 for i in full))
    def test_one_winning_period_cannot_pass(self):
        periods={str(i):dict(base=dict(net_pnl=100 if i==0 else -1)) for i in range(4)}
        cont=dict(base=dict(trades=100,profit_factor=2,close_mtm_drawdown_pct=1,intrabar_drawdown_bound_pct=2),
                  stress=dict(net_pnl=100),mean_daily_pnl_95pct_block_bootstrap=[1,2])
        self.assertIn('fewer_than_3_profitable_blocks',discovery_failures(periods,cont))
