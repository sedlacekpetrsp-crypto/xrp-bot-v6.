import importlib.util,pathlib,unittest
spec=importlib.util.spec_from_file_location('replay',pathlib.Path(__file__).with_name('run.py'));r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
class TimeSafety(unittest.TestCase):
 def rows(self):return [[i*300000,100,102,99,101,10,i*300000+299999] for i in range(6)]
 def test_aggregate_available_only_after_close(self):
  rows=r.aggregate(self.rows(),3);ends=[b[6] for b in rows]
  self.assertEqual(r.closed(rows,ends,899999),[])
  self.assertEqual(len(r.closed(rows,ends,900000)),1)
  self.assertEqual(rows[0],[0,100,102,99,101,30,899999])
 def test_future_bar_does_not_change_past_input(self):
  rows=r.aggregate(self.rows(),3);end=[x[6] for x in rows]
  before=r.closed(rows,end,900000)
  rows[-1][4]=100000
  self.assertEqual(before,r.closed(rows,end,900000))
 def test_gap_rejected(self):
  rows=self.rows();rows[1][0]+=300000
  with self.assertRaises(ValueError):r.aggregate(rows,3)
class ExecutionSafety(unittest.TestCase):
 def simulate(self,gap=False):
  import copy
  from contextlib import ExitStack
  from unittest.mock import patch
  from datetime import datetime,timezone
  replay=r.Replay.__new__(r.Replay);replay.clock=0
  rows=[[i*300000,100.1,100.5,99.5,100.1,10,i*300000+299999] for i in range(24)]
  if gap:rows[13][1:5]=[97,98,96,97]
  else:rows[12][2:4]=[106,98]
  replay.data={symbol:copy.deepcopy(rows) for symbol in r.P['symbols']}
  signals={3600000:[dict(symbol='BTCUSDT',candidate=dict(side='LONG',entry=100,stop=99,tp=105,key='test',strategy='FIB_618_786'))]}
  saved=copy.deepcopy(r.w.state)
  try:
   with ExitStack() as stack:
    for name,value in [('save_state',lambda:None),('save_trade',lambda *a:None),('utcnow',lambda:datetime.fromtimestamp(replay.clock/1000,timezone.utc)),('portfolio_risk_allowance',lambda *a:(9.18,{'risk_cap_usdc':9.18}))]:
     stack.enter_context(patch.object(r.w,name,value,create=True))
    stack.enter_context(patch.object(r.w.paper_stop_policy,'MULTIPLIER',1.15))
    return replay.run(signals,3600000,4200000,.0002)
  finally:r.w.state.clear();r.w.state.update(saved)
 def test_same_bar_stop_and_target_uses_stop_and_next_open(self):
  result,trades=self.simulate()
  self.assertEqual(len(trades),1)
  self.assertEqual(trades[0]['reason'],'SL')
  self.assertAlmostEqual(trades[0]['entry'],100.1*1.0002)
  self.assertAlmostEqual(result['net_pnl'],-9.18)
 def test_gap_fills_at_worse_open_not_ideal_stop(self):
  result,trades=self.simulate(True)
  self.assertEqual(trades[0]['reason'],'GAP_SL')
  self.assertAlmostEqual(trades[0]['exit'],97*.9998)
  self.assertLess(result['net_pnl'],-9.18)
if __name__=='__main__':unittest.main()
