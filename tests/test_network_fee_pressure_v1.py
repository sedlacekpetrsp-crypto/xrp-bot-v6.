import unittest
from dataclasses import replace
from research.network_fee_pressure_v1 import Config,DAY,backtest,rank,signal_at
def row(i,p=1,fee=1,tx=100):return dict(timestamp=i*DAY,open=p,high=p*1.02,low=p*.98,close=p,fee_total=fee,transfer_count=tx)
class Tests(unittest.TestCase):
 def test_rank(self):self.assertEqual(rank(range(1,101),.85),85)
 def test_lag(self):
  r=[row(i) for i in range(94)];r[90]['fee_total']=10;self.assertFalse(signal_at(r,90));self.assertTrue(signal_at(r,91))
 def test_timing_overlap(self):
  r=[row(i) for i in range(120)]
  for k in (90,100,110):r[k]['fee_total']=10
  t,_=backtest(r,0,120*DAY,replace(Config(),max_hold=2,fee=0,slippage=0));self.assertTrue(all(x['entry_timestamp']==x['metric_timestamp']+2*DAY for x in t));self.assertTrue(all(b['entry_timestamp']>a['exit_timestamp'] for a,b in zip(t,t[1:])))
 def test_costs(self):
  r=[row(i) for i in range(100)];r[90]['fee_total']=10;a,_=backtest(r,0,100*DAY,replace(Config(),max_hold=2,fee=0,slippage=0));b,_=backtest(r,0,100*DAY,replace(Config(),max_hold=2));self.assertLess(b[0]['pnl'],a[0]['pnl'])
 def test_gap_stop(self):
  r=[row(i) for i in range(100)];r[90]['fee_total']=10;r[93].update(open=.8,high=.9,low=.79,close=.85);t,_=backtest(r,0,100*DAY);self.assertEqual(t[0]['reason'],'GAP_STOP')
 def test_fold_end(self):
  r=[row(i) for i in range(94)];r[90]['fee_total']=10;t,_=backtest(r,0,93*DAY);self.assertEqual(t[-1]['reason'],'END')
if __name__=='__main__':unittest.main()
