import unittest
from dataclasses import replace
from research.ledger_activity_breadth_v1 import Config,DAY,backtest,nearest_rank,signal_at

def row(i,price=1,adr=100,tx=1000):
    return dict(timestamp=i*DAY,open=price,high=price*1.02,low=price*.98,close=price,active_addresses=adr,tx_count=tx)

class Tests(unittest.TestCase):
    def test_nearest_rank(self): self.assertEqual(nearest_rank(range(1,11),.8),8)
    def test_two_day_metric_lag(self):
        r=[row(i) for i in range(94)]; r[90]["active_addresses"]=1000; r[90]["tx_count"]=2000
        self.assertFalse(signal_at(r,90)); self.assertFalse(signal_at(r,90+0)); self.assertTrue(signal_at(r,91))
    def test_next_open_nonoverlap(self):
        r=[row(i) for i in range(120)]
        for k in (90,103): r[k]["active_addresses"]=1000; r[k]["tx_count"]=2000
        c=replace(Config(),fee=0,slippage=0,max_hold=2)
        t,_=backtest(r,0,120*DAY,c); self.assertTrue(all(x["entry_timestamp"]==x["signal_timestamp"]+DAY for x in t)); self.assertTrue(all(b["entry_timestamp"]>a["exit_timestamp"] for a,b in zip(t,t[1:])))
    def test_cost_stress_hurts(self):
        r=[row(i) for i in range(100)]; r[90]["active_addresses"]=1000; r[90]["tx_count"]=2000
        a,_=backtest(r,0,100*DAY,replace(Config(),fee=0,slippage=0,max_hold=2)); b,_=backtest(r,0,100*DAY,replace(Config(),max_hold=2))
        self.assertLess(b[0]["pnl"],a[0]["pnl"])
    def test_gap_suppresses(self):
        r=[row(i) for i in range(95)]; del r[50]
        self.assertFalse(signal_at(r,91))
    def test_gap_stop(self):
        r=[row(i) for i in range(100)]; r[90]["active_addresses"]=1000; r[90]["tx_count"]=2000; r[93]["open"]=.8; r[93]["low"]=.79; r[93]["high"]=.9; r[93]["close"]=.85
        t,_=backtest(r,0,100*DAY,Config()); self.assertEqual(t[0]["reason"],"GAP_STOP")
    def test_fold_end_liquidates(self):
        r=[row(i) for i in range(94)]; r[90]["active_addresses"]=1000; r[90]["tx_count"]=2000
        t,_=backtest(r,0,93*DAY,Config()); self.assertEqual(t[-1]["reason"],"END"); self.assertLess(t[-1]["exit_timestamp"],93*DAY)

if __name__=="__main__": unittest.main()
