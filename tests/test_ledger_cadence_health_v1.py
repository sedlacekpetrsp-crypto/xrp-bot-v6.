import unittest
from dataclasses import replace
from research.ledger_cadence_health_v1 import Config,DAY,make_signals,backtest
def prices(n=70,p=100.):return [dict(timestamp=i*DAY,open=p,high=p+1,low=p-1,close=p) for i in range(n)]
class Tests(unittest.TestCase):
 def test_signal_lag_and_prefix(self):
  m=[dict(timestamp=i*DAY,block_count=22000) for i in range(30)];a=make_signals(m);b=make_signals(m[:20]);self.assertEqual(b,{k:v for k,v in a.items() if k<=21*DAY});self.assertEqual(a[15*DAY]['metric_timestamp'],13*DAY)
 def test_thresholds(self):
  m=[dict(timestamp=i*DAY,block_count=22000) for i in range(20)];m[-1]['block_count']=19999;self.assertNotIn(21*DAY,make_signals(m))
 def test_costs_sizing_overlap(self):
  r=prices();s=dict(metric_timestamp=18*DAY,median_14=22000,min_7=22000);r[20]['cadence_signal']=s;r[21]['cadence_signal']=dict(s,metric_timestamp=19*DAY);r[31]['cadence_signal']=dict(s,metric_timestamp=29*DAY);t,_=backtest(r,0,100*DAY);self.assertEqual(len(t),2);self.assertAlmostEqual(t[0]['entry'],100.02);self.assertLessEqual(t[0]['leg_notional'],2000.00001)
 def test_stop_first_gap(self):
  r=prices();r[20]['cadence_signal']=dict(metric_timestamp=18*DAY,median_14=22000,min_7=22000);r[20].update(high=110,low=90);self.assertEqual(backtest(r,0,100*DAY)[0][0]['reason'],'STOP')
  r=prices();r[20]['cadence_signal']=dict(metric_timestamp=18*DAY,median_14=22000,min_7=22000);r[21].update(open=90,high=91,low=89,close=90);t=backtest(r,0,100*DAY)[0][0];self.assertEqual((t['reason'],t['raw_exit']),('GAP_STOP',90))
 def test_stress_hurts(self):
  r=prices();r[20]['cadence_signal']=dict(metric_timestamp=18*DAY,median_14=22000,min_7=22000);a=backtest(r,0,100*DAY)[0][0];b=backtest(r,0,100*DAY,replace(Config(),fee=.0019,slippage=.0004))[0][0];self.assertLess(b['pnl'],a['pnl'])
if __name__=='__main__':unittest.main()
