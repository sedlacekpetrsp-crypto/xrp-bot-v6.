import unittest
from dataclasses import replace
from research.xrp_bank_credit_expansion_v1 import Config,DAY,atr,backtest,make_signals,validate_prices

def bars(n=40,price=100.):
    return [{'timestamp':i*DAY,'open':price,'high':price+1,'low':price-1,'close':price} for i in range(n)]
class BankCreditTests(unittest.TestCase):
    def test_signal_uses_observation_lag_and_growth(self):
        macro=[{'timestamp':i*7*DAY,'value':100+i} for i in range(20)]; signals=make_signals(macro,Config(minimum_growth=.10)); self.assertIn(15*7*DAY,signals); s=signals[15*7*DAY]; self.assertEqual((s['metric_timestamp'],s['earlier_timestamp']),(13*7*DAY,0))
    def test_signal_rejects_nonpositive(self):
        with self.assertRaises(ValueError): make_signals([{'timestamp':0,'value':0}])
    def test_price_validation(self):
        x=bars(2); x[1]['low']=200
        with self.assertRaises(ValueError): validate_prices(x)
    def test_atr_requires_contiguous_history(self):
        x=bars(20); x[10]['timestamp']+=DAY
        self.assertIsNone(atr(x,14,14))
    def test_next_open_nonoverlap_and_cap(self):
        x=bars(); x[14].update(macro_signal=True,metric_timestamp=12*DAY,earlier_timestamp=0,earlier_credit=100,latest_credit=102,credit_growth=.02); x[15]['high']=110
        trades,_=backtest(x,0,40*DAY,Config(atr_n=14)); self.assertEqual(len(trades),1); self.assertEqual(trades[0]['entry_timestamp'],15*DAY); self.assertLessEqual(trades[0]['leg_notional'],2000.000001)
    def test_stop_first_and_gap_stop(self):
        x=bars(); x[14].update(macro_signal=True,metric_timestamp=12*DAY,earlier_timestamp=0,earlier_credit=100,latest_credit=102,credit_growth=.02); x[16].update(open=90,high=101,low=89,close=100)
        t,_=backtest(x,0,40*DAY,Config(atr_n=14)); self.assertEqual(t[0]['reason'],'GAP_STOP')
    def test_stress_costs_are_worse(self):
        x=bars(); x[14].update(macro_signal=True,metric_timestamp=12*DAY,earlier_timestamp=0,earlier_credit=100,latest_credit=102,credit_growth=.02); x[22].update(open=102,high=103,low=101,close=102)
        a,_=backtest(x,0,40*DAY,Config(atr_n=14)); b,_=backtest(x,0,40*DAY,replace(Config(atr_n=14),fee=.0019,slippage=.0004)); self.assertLess(b[0]['pnl'],a[0]['pnl'])
    def test_intratrade_drawdown_is_marked(self):
        x=bars(); x[14].update(macro_signal=True,metric_timestamp=12*DAY,earlier_timestamp=0,earlier_credit=100,latest_credit=102,credit_growth=.02); x[15].update(low=98,high=101)
        trades,curve=backtest(x,0,40*DAY,Config(atr_n=14)); self.assertLess(trades[0]['intratrade_min_equity'],trades[0]['entry_equity']); self.assertIn(trades[0]['intratrade_min_equity'],[p['equity'] for p in curve])
if __name__=='__main__': unittest.main()
