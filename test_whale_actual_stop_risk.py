import copy
import unittest
from unittest.mock import patch
import app_blue_whale_mirror as w
import paper_stop_policy as policy


class ActualStopRiskTests(unittest.TestCase):
    def setUp(self):
        self.saved=copy.deepcopy(w.state)
        w.state.update(balance=10000.,equity=10000.,open_positions=[],trades=[],seen_signal_ids=[],market_prices={})

    def tearDown(self):
        w.state.clear();w.state.update(self.saved)

    def signal(self,stop=99):
        return dict(id=123,symbol='BTCUSDT',strategy='FIB_618_786',text='LONG',entry=100,tp=105,
                    stop=dict(low=stop,high=stop,raw=str(stop),masked=False))

    def test_widened_cap_sized_entry_rejected_without_account_mutation(self):
        before=copy.deepcopy(w.state)
        with patch.object(policy,'MULTIPLIER',1.15),patch.object(w,'save_state'),patch.object(w,'portfolio_risk_allowance',create=True,return_value=(9.18,{'risk_cap_usdc':9.18})):
            self.assertFalse(w.open_paper(self.signal(),'LONG',100))
        for key in ('balance','equity','open_positions','trades','seen_signal_ids'):
            self.assertEqual(w.state[key],before[key])
        self.assertGreater(w.state['last_signal']['stop_loss_risk_net'],9.18)

    def test_notional_limited_entry_keeps_quantity_and_target(self):
        quantities=[]
        for multiplier in (1.,1.15):
            w.state.update(balance=10000.,equity=10000.,open_positions=[dict(symbol='ETHUSDT',side='LONG',entry=100,stop=102,qty=95,entry_fee=0,notional=9500,risk_dollars=0)],trades=[],seen_signal_ids=[])
            with patch.object(policy,'MULTIPLIER',multiplier),patch.object(w,'save_state'),patch.object(w,'portfolio_risk_allowance',create=True,return_value=(12.,{'risk_cap_usdc':12.})):
                self.assertTrue(w.open_paper(self.signal(99.75),'LONG',100))
            p=w.state['open_positions'][-1];quantities.append(p['qty'])
            self.assertEqual(p['tp'],105)
            self.assertAlmostEqual(p['actual_risk_rate']*10000,policy.net_stop_risk(p,w.FEE_RATE,w.SLIPPAGE_RATE))
        self.assertEqual(*quantities)

    def test_risk_matches_real_stop_close_for_both_sides(self):
        for side,stop in (('LONG',98),('SHORT',102)):
            p=dict(entry=100,stop=stop,qty=3,side=side)
            sign=1 if side=='LONG' else -1
            fill=stop*(1-sign*.0002)
            net=sign*(fill-100)*3-(fill+100)*3*.00095
            self.assertAlmostEqual(policy.net_stop_risk(p,.00095,.0002),-net)
        self.assertEqual(policy.net_stop_risk(dict(entry=100,stop=102,qty=3,side='LONG'),.00095,.0002),0)

    def test_existing_widened_stop_counts_toward_total(self):
        existing=dict(entry=100,stop=95,qty=1,side='LONG')
        w.state['open_positions']=[dict(existing,symbol='ETHUSDT',entry_fee=0,notional=100,risk_dollars=0)]
        with patch.object(w,'MAX_TOTAL_RISK_RATE',.0013),patch.object(w,'save_state'):
            self.assertFalse(w.open_paper(self.signal(),'LONG',100))
        self.assertEqual(len(w.state['open_positions']),1)
        self.assertEqual(w.state['balance'],10000)


if __name__=='__main__':unittest.main()
