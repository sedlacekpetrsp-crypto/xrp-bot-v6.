import datetime as dt
import unittest
from dataclasses import replace
from research.btc_asset_manager_accumulation_xrp_v1 import Config,DAY,backtest,make_signals,next_monday
UTC=dt.timezone.utc
def stamp(y,m,d): return int(dt.datetime(y,m,d,tzinfo=UTC).timestamp()*1000)
class Tests(unittest.TestCase):
    def reports(self):
        base=stamp(2024,1,2)
        return [dict(timestamp=base+i*7*DAY,open_interest=1000,asset_manager_long=200+i,asset_manager_short=150) for i in range(60)]
    def prices(self,n=90):
        base=stamp(2024,1,1)
        return [dict(timestamp=base+i*DAY,open=1.,high=1.03,low=.98,close=1.01) for i in range(n)]
    def signal(self,entry): return {entry:dict(report_timestamp=entry-6*DAY,net_share=.1,median52=.05,share_four_reports_ago=.08,open_interest=1000,asset_manager_long=200,asset_manager_short=100)}
    def test_strict_next_monday(self):
        self.assertEqual(next_monday(stamp(2026,11,3)),stamp(2026,11,9)); self.assertEqual(next_monday(stamp(2026,11,2)),stamp(2026,11,9))
    def test_prefix_invariance(self):
        r=self.reports(); a=make_signals(r); r[-1]["asset_manager_long"]=999; b=make_signals(r); e=next_monday(r[-2]["timestamp"]); self.assertEqual(a.get(e),b.get(e))
    def test_duplicate_report_rejected(self):
        r=self.reports(); r[3]["timestamp"]=r[2]["timestamp"]
        with self.assertRaises(ValueError): make_signals(r)
    def test_stress_adverse(self):
        rows=self.prices(); e=next(x["timestamp"] for x in rows[20:] if dt.datetime.fromtimestamp(x["timestamp"]/1000,UTC).weekday()==0)
        a,_=backtest(rows,self.signal(e),rows[0]["timestamp"],rows[-1]["timestamp"]+DAY); b,_=backtest(rows,self.signal(e),rows[0]["timestamp"],rows[-1]["timestamp"]+DAY,replace(Config(),fee=.0019,slippage=.0004)); self.assertEqual(len(a),1); self.assertLess(b[0]["pnl"],a[0]["pnl"])
    def test_gap_stop_and_nonoverlap(self):
        rows=self.prices(); es=[x["timestamp"] for x in rows[20:] if dt.datetime.fromtimestamp(x["timestamp"]/1000,UTC).weekday()==0][:2]; signals={}; [signals.update(self.signal(e)) for e in es]; i=next(i for i,x in enumerate(rows) if x["timestamp"]==es[0]); rows[i+1].update(open=.8,high=.82,low=.79,close=.81); t,_=backtest(rows,signals,rows[0]["timestamp"],rows[-1]["timestamp"]+DAY); self.assertEqual(t[0]["reason"],"GAP_STOP"); self.assertEqual(t[0]["raw_exit"],.8); self.assertTrue(all(a["exit_timestamp"]<b["entry_timestamp"] for a,b in zip(t,t[1:])))
    def test_fold_end_realized(self):
        rows=self.prices(30); e=next(x["timestamp"] for x in rows[20:] if dt.datetime.fromtimestamp(x["timestamp"]/1000,UTC).weekday()==0); t,_=backtest(rows,self.signal(e),rows[0]["timestamp"],e+2*DAY); self.assertEqual(t[0]["reason"],"FOLD_END"); self.assertLess(t[0]["exit_timestamp"],e+2*DAY)
if __name__=='__main__': unittest.main()
