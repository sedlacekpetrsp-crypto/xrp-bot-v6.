import datetime as dt,unittest
from dataclasses import replace
from research.xrp_session_handoff_reversal_v1 import Config,STEP,backtest,make_signals
UTC=dt.timezone.utc
def stamp(y,m,d,h=0): return int(dt.datetime(y,m,d,h,tzinfo=UTC).timestamp()*1000)
class Tests(unittest.TestCase):
 def bars(self,n=80):
  base=stamp(2024,1,1); return [dict(timestamp=base+i*STEP,open=1.,high=1.01,low=.99,close=1.) for i in range(n)]
 def set_signal(self,b):
  b[0]['open']=1.; b[7]['close']=.98; b[7]['low']=.97
 def test_exact_session_and_entry(self):
  b=self.bars(); self.set_signal(b); s=make_signals(b); self.assertIn(stamp(2024,1,1,8),s); self.assertLessEqual(s[stamp(2024,1,1,8)]['session_return'],-.015)
 def test_gap_suppresses(self):
  b=self.bars(); self.set_signal(b); del b[4]; self.assertNotIn(stamp(2024,1,1,8),make_signals(b))
 def test_prefix_invariance(self):
  b=self.bars(); self.set_signal(b); a=make_signals(b); b[-1]['close']=.5; b[-1]['low']=.4; self.assertEqual(a.get(stamp(2024,1,1,8)),make_signals(b).get(stamp(2024,1,1,8)))
 def test_stress_and_limits(self):
  b=self.bars(); self.set_signal(b); s=make_signals(b); a,_=backtest(b,s,b[0]['timestamp'],b[-1]['timestamp']+STEP); z,_=backtest(b,s,b[0]['timestamp'],b[-1]['timestamp']+STEP,replace(Config(),fee=.0019,slippage=.0004)); self.assertEqual(len(a),1); self.assertLess(z[0]['pnl'],a[0]['pnl']); self.assertLessEqual(a[0]['leg_notional'],a[0]['entry_equity']*.2+1e-8)
 def test_gap_stop_worse_open(self):
  b=self.bars(); self.set_signal(b); b[9].update(open=.90,high=.91,low=.89,close=.90); s=make_signals(b); t,_=backtest(b,s,b[0]['timestamp'],b[-1]['timestamp']+STEP); self.assertEqual(t[0]['reason'],'GAP_STOP'); self.assertEqual(t[0]['raw_exit'],.90)
 def test_fold_end_realized(self):
  b=self.bars(); self.set_signal(b); s=make_signals(b); e=stamp(2024,1,1,10); t,_=backtest(b,s,b[0]['timestamp'],e); self.assertEqual(t[0]['reason'],'FOLD_END'); self.assertLess(t[0]['exit_timestamp'],e)
if __name__=='__main__': unittest.main()
