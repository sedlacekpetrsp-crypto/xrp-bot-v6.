import unittest
from dataclasses import replace
from research.spot_perp_carry_v1 import Config,STEP,backtest

def bars(n=220,spot=100,mark=100.2):
    return [dict(timestamp=i*STEP,spot_open=spot,spot_high=spot*1.001,spot_low=spot*.999,spot_close=spot,mark_open=mark,mark_high=mark*1.001,mark_low=mark*.999,mark_close=mark) for i in range(n)]

def funding(n=220,rate=.0004): return [dict(timestamp=i*STEP,rate=rate) for i in range(0,n,8)]

class CarryTests(unittest.TestCase):
    def test_next_open_and_time_exit(self):
        t,_=backtest(bars(),funding(),0,220*STEP)
        self.assertEqual(t[0]["entry_timestamp"],STEP)
        self.assertEqual(t[0]["exit_timestamp"],169*STEP)
        self.assertEqual(t[0]["reason"],"TIME")

    def test_funding_boundaries(self):
        t,_=backtest(bars(20),funding(20),0,20*STEP,replace(Config(),max_hold=9))
        self.assertEqual(t[0]["funding_count"],1)
        self.assertGreater(t[0]["funding_cash"],0)

    def test_no_overlap(self):
        t,_=backtest(bars(400),funding(400),0,400*STEP)
        self.assertTrue(all(a["exit_timestamp"]<b["entry_timestamp"] for a,b in zip(t,t[1:])))

    def test_double_cost_worse(self):
        base,_=backtest(bars(),funding(),0,220*STEP)
        stress,_=backtest(bars(),funding(),0,220*STEP,replace(Config(),spot_fee=.0019,perp_fee=.001,slippage=.0004))
        self.assertLess(stress[0]["pnl"],base[0]["pnl"])

    def test_gap_stop(self):
        x=bars(10); x[2].update(spot_open=98,spot_high=98.1,spot_low=97.9,spot_close=98,mark_open=100.5,mark_high=100.6,mark_low=100.4,mark_close=100.5)
        t,_=backtest(x,funding(10),0,10*STEP)
        self.assertEqual(t[0]["reason"],"GAP_STOP")

    def test_intrabar_stop_conservative(self):
        x=bars(10); x[2]["spot_low"]=98; x[2]["mark_high"]=101
        t,_=backtest(x,funding(10),0,10*STEP)
        self.assertEqual(t[0]["reason"],"STOP")
        self.assertEqual(t[0]["raw_spot_exit"],98)
        self.assertEqual(t[0]["raw_mark_exit"],101)

    def test_gap_liquidates_last_close(self):
        x=bars(10); x[3]["timestamp"]=4*STEP
        for j in range(4,10): x[j]["timestamp"]=(j+1)*STEP
        t,_=backtest(x,funding(12),0,12*STEP)
        self.assertEqual(t[0]["reason"],"DATA_GAP")
        self.assertEqual(t[0]["exit_timestamp"],2*STEP)

    def test_position_cap(self):
        t,_=backtest(bars(10),funding(10),0,10*STEP)
        self.assertAlmostEqual(t[0]["leg_notional"],1000)

    def test_prefix_invariance(self):
        full,_=backtest(bars(220),funding(220),0,220*STEP,replace(Config(),max_hold=20))
        prefix,_=backtest(bars(100),funding(100),0,100*STEP,replace(Config(),max_hold=20))
        self.assertEqual([(t["entry_timestamp"],t["pnl"]) for t in full if t["exit_timestamp"]<99*STEP],[(t["entry_timestamp"],t["pnl"]) for t in prefix if t["reason"]!="END"])

    def test_signal_threshold(self):
        t,_=backtest(bars(10),funding(10,.0001),0,10*STEP)
        self.assertEqual(t,[])

if __name__=="__main__": unittest.main()
