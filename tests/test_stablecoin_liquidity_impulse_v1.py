import unittest
from dataclasses import replace
from research.stablecoin_liquidity_impulse_v1 import Config,DAY,backtest,growth,signal_at
def row(i,p=1,s=100):return dict(timestamp=i*DAY,open=p,high=p*1.02,low=p*.98,close=p,stable_supply=s)
class Tests(unittest.TestCase):
 def test_growth(self):
  r=[row(i,s=100+i)for i in range(8)];self.assertAlmostEqual(growth(r,7,7),.07)
 def test_lag(self):
  r=[row(i)for i in range(200)];r[187]['stable_supply']=110;self.assertFalse(signal_at(r,187));self.assertTrue(signal_at(r,188))
 def test_timing_overlap(self):
  r=[row(i)for i in range(240)]
  for k in(187,210,230):r[k]['stable_supply']=110
  t,_=backtest(r,0,240*DAY,replace(Config(),max_hold=2,fee=0,slippage=0));self.assertTrue(all(x['entry_timestamp']==x['metric_timestamp']+2*DAY for x in t));self.assertTrue(all(b['entry_timestamp']>a['exit_timestamp']for a,b in zip(t,t[1:])))
 def test_costs(self):
  r=[row(i)for i in range(200)];r[187]['stable_supply']=110;a,_=backtest(r,0,200*DAY,replace(Config(),max_hold=2,fee=0,slippage=0));b,_=backtest(r,0,200*DAY,replace(Config(),max_hold=2));self.assertLess(b[0]['pnl'],a[0]['pnl'])
 def test_gap_stop(self):
  r=[row(i)for i in range(200)];r[187]['stable_supply']=110;r[190].update(open=.8,high=.9,low=.79,close=.85);t,_=backtest(r,0,200*DAY);self.assertEqual(t[0]['reason'],'GAP_STOP')
 def test_gap_suppresses(self):
  r=[row(i)for i in range(200)];del r[100];r[187]['stable_supply']=110;self.assertFalse(signal_at(r,188))
if __name__=='__main__':unittest.main()
