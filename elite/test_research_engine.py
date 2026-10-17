import unittest
from elite.research_engine import Decision,simulate,decisions,aggregate,validate

class ResearchEngineTests(unittest.TestCase):
    def rows(self,n=10):return [(i*300000,100.,100.,100.,100.) for i in range(n)]
    def test_next_open_and_boundary(self):
        r=self.rows(); sig={1:Decision(10)}
        trade=simulate(r,sig,2)['trade_log'][0]
        self.assertEqual(trade['entry_index'],2)
        self.assertEqual(trade['exit_index'],9)
        self.assertEqual(trade['reason'],'BOUNDARY')
        self.assertEqual(simulate(r,sig,3)['trades'],0)
    def test_cost_accounting(self):
        result=simulate(self.rows(),{0:Decision(10)})
        self.assertLess(result['net_pnl'],0)
        self.assertAlmostEqual(result['net_pnl'],-result['costs'])
        self.assertAlmostEqual(sum(t['pnl'] for t in result['trade_log']),result['net_pnl'])
    def test_gap_stop(self):
        r=self.rows();r[3]=(900000,80.,82.,79.,80.)
        result=simulate(r,{0:Decision(5)},fee=0,slip=0,half_spread=0)
        self.assertEqual(result['trade_log'][0]['reason'],'STOP_GAP')
        self.assertAlmostEqual(result['net_pnl'],-200)
    def test_stop_precedes_target(self):
        r=self.rows();r[1]=(300000,100.,110.,90.,100.)
        result=simulate(r,{0:Decision(5,5)},fee=0,slip=0,half_spread=0)
        self.assertEqual(result['trade_log'][0]['reason'],'STOP')
        self.assertAlmostEqual(result['net_pnl'],-50)
    def test_open_drawdown_is_measured(self):
        r=self.rows();r[3]=(900000,100.,100.,90.,90.)
        result=simulate(r,{0:Decision(20)},fee=0,slip=0,half_spread=0)
        self.assertEqual(result['net_pnl'],0)
        self.assertGreater(result['close_mtm_drawdown_pct'],0)
        self.assertGreaterEqual(result['intrabar_drawdown_bound_pct'],result['close_mtm_drawdown_pct'])
    def test_signal_exit_next_open(self):
        r=self.rows();r[3]=(900000,110.,110.,110.,110.)
        result=simulate(r,{0:Decision(20),2:Decision(exit=True)},fee=0,slip=0,half_spread=0)
        self.assertEqual(result['trade_log'][0]['exit_index'],3)
        self.assertEqual(result['net_pnl'],25)
    def test_no_incomplete_aggregate(self):
        self.assertEqual(len(aggregate(self.rows(23),12)),1)
        self.assertEqual(aggregate(self.rows(23),12)[0][0],11)
    def test_invalid_prices_and_missing_bar(self):
        for r in ([(0,1.,float('nan'),1.,1.)],[(0,1.,1.,1.,1.),(600000,1.,1.,1.,1.)]):
            with self.assertRaises(ValueError):validate(r)
    def test_future_cannot_change_past_signals(self):
        # Changing all future prices must leave every earlier decision unchanged.
        r=[(i*300000,100+i*.01,101+i*.01,99+i*.01,100+i*.01) for i in range(11000)]
        cutoff=10001
        for name in ('v5','v6','v7'):
            before=decisions(r[:cutoff],name)
            full=decisions(r,name)
            self.assertEqual(before,{i:d for i,d in full.items() if i<cutoff})
            changed=r[:cutoff]+[(t,o*3,h*3,l*3,c*3) for t,o,h,l,c in r[cutoff:]]
            self.assertEqual(before,{i:d for i,d in decisions(changed,name).items() if i<cutoff})

if __name__=='__main__':unittest.main()
