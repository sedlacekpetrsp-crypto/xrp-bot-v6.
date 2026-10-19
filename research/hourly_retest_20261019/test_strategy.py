import unittest
from research.hourly_retest_20261019.strategy import hourly_rows,hourly_signals
from research.candle_validation_20261019.engine import signals
P=dict(lookback=20,retest_expiry_bars=4,retest_tolerance_atr=.25)
def bars(n):
 out=[]
 for i in range(n):
  x=100+i*.02+(i%23)*.1
  out.append([i*900000,x,x+.3,x-.3,x+.1,10,(i+1)*900000-1])
 return out
class HourlyTests(unittest.TestCase):
 def test_aggregate_and_mapping(self):
  rows=bars(1200);h,ends=hourly_rows(rows);s,a=signals(h,'breakout_retest',P);m,v=hourly_signals(rows,P)
  self.assertEqual(h[0][1],rows[0][1]);self.assertEqual(h[0][4],rows[3][4]);self.assertEqual(h[0][5],40)
  self.assertEqual(h[0][2],max(r[2] for r in rows[:4]))
  for j,i in enumerate(ends):self.assertEqual((m[i],v[i]),(s[j],a[j]))
  self.assertTrue(all(m[i]==v[i]==0 for i in range(len(rows)) if i%4!=3))
 def test_incomplete_hour_and_future_invariance(self):
  rows=bars(1200);full=hourly_signals(rows,P)
  for n in (1001,1002,1003,1004):
   prefix=hourly_signals(rows[:n],P);complete=n//4*4
   self.assertEqual(prefix[0][:complete],full[0][:complete]);self.assertEqual(prefix[1][:complete],full[1][:complete])
   self.assertTrue(all(x==0 for x in prefix[0][complete:]))
 def test_gap_rejected(self):
  rows=bars(8);rows[2][0]+=900000
  with self.assertRaises(ValueError):hourly_rows(rows)
