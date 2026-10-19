import copy,json,pathlib,unittest
from research.candle_validation_20261019.engine import features,signals,open_position,pnl,exit_price,replay
P=json.loads(pathlib.Path('research/candle_validation_20261019/protocol.json').read_text())
def bars(n=300):
 return [[i*900000,100+i*.1,101+i*.1,99+i*.1,100.5+i*.1,10,(i+1)*900000-1] for i in range(n)]
class CandleTests(unittest.TestCase):
 def test_prefix_invariance(self):
  r=bars()
  for name in P['strategies']:
   a,_=signals(r[:260],name,P);b,_=signals(r,name,P);self.assertEqual(a,b[:260])
 def test_hour_changes_only_at_close(self):
  f=features(bars());self.assertEqual(f['trend'][199],f['trend'][200]);self.assertEqual(f['trend'][198],0)
 def test_stop_priority_and_gap(self):
  p=dict(side=1,stop=99,target=102)
  self.assertEqual(exit_price(p,[0,100,103,98]),(99,'STOP'))
  self.assertEqual(exit_price(p,[0,98,103,97]),(98,'STOP_GAP'))
  self.assertEqual(exit_price(dict(side=-1,stop=102,target=99),[0,100,103,98]),(102,'STOP'))
 def test_target_gap_precedes_later_stop(self):
  self.assertEqual(exit_price(dict(side=1,stop=99,target=102),[0,103,104,98]),(102,'TARGET_GAP'))
  self.assertEqual(exit_price(dict(side=-1,stop=102,target=99),[0,98,103,97]),(99,'TARGET_GAP'))
 def test_widen_stop_without_changing_qty_or_target(self):
  a=open_position(1,100,1,P,.0002);q=dict(P,stop_multiplier=1);b=open_position(1,100,1,q,.0002)
  self.assertEqual(a['qty'],b['qty']);self.assertEqual(a['target'],b['target'])
  self.assertAlmostEqual((a['entry']-a['stop'])/(b['entry']-b['stop']),1.15)
 def test_roundtrip_costs_both_sides(self):
  for side in (1,-1):
   a=open_position(side,100,1,P,.0002);net,fees,gross=pnl(a,100,P['fee_per_side'],.0002)
   self.assertLess(net,0);self.assertGreater(fees,1.8);self.assertAlmostEqual(net,gross-fees)
 def test_entry_next_open_and_cash_reconcile(self):
  rows=bars(3);s=[1,0,0];r,t=replay(rows,s,[10]*3,0,2700000,P,.0002)
  self.assertEqual(t[0]['opened_at'],900000);self.assertAlmostEqual(t[0]['entry'],float(rows[1][1])*1.0002)
  self.assertEqual(t[0]['reason'],'PERIOD_END');self.assertAlmostEqual(r['net_pnl'],sum(x['net_pnl'] for x in t))
if __name__=='__main__':unittest.main()
