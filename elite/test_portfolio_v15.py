import unittest
from elite.research_engine import Decision,simulate
from elite.portfolio_v15 import Router,regime_series

class RoutingTests(unittest.TestCase):
    def rows(self,n=10):return [(i*300000,100.,100.,100.,100.) for i in range(n)]
    def test_component_parity(self):
        rows=self.rows();sig={0:Decision(10),3:Decision(exit=True)}
        old=simulate(rows,sig);new=simulate(rows,Router({'a':sig},('a',)))
        for k in old:
            if k!='trade_log':self.assertEqual(old[k],new[k])
        cleaned=[{k:v for k,v in t.items() if k!='source'} for t in new['trade_log']]
        self.assertEqual(old['trade_log'],cleaned)
    def test_exit_ownership(self):
        streams={'a':{0:Decision(10),5:Decision(exit=True)},'b':{2:Decision(exit=True),3:Decision(10)}}
        result=simulate(self.rows(),Router(streams,('a','b')))
        self.assertEqual(result['trades'],1)
        self.assertEqual(result['trade_log'][0]['exit_index'],6)
        self.assertEqual(result['trade_log'][0]['source'],'a')
    def test_priority_and_shared_cash(self):
        streams={'a':{0:Decision(10)},'b':{0:Decision(20)}}
        result=simulate(self.rows(),Router(streams,('b','a')))
        self.assertEqual(result['trades'],1)
        self.assertEqual(result['trade_log'][0]['source'],'b')
        expected=simulate(self.rows(),streams['b'])
        self.assertEqual(result['net_pnl'],expected['net_pnl'])
    def test_regime_only_filters_entries(self):
        r=Router({'v5':{0:Decision(10),1:Decision(exit=True)},'v8':{0:Decision(20)}},('v5','v8'),{0:True,1:False})
        self.assertEqual(r.for_position(0).source,'v5')
        self.assertTrue(r.for_position(1,'v5').exit)
    def test_regime_prefix_invariance(self):
        rows=[(i*300000,100+i*.01,101+i*.01,99+i*.01,100+i*.01) for i in range(3000)]
        cut=2501
        self.assertEqual(regime_series(rows[:cut]),{i:v for i,v in regime_series(rows).items() if i<cut})
    def test_no_same_open_reentry_after_exit(self):
        r=Router({'a':{0:Decision(10),3:Decision(exit=True)},'b':{3:Decision(10)}},('a','b'))
        self.assertEqual(simulate(self.rows(),r)['trades'],1)
