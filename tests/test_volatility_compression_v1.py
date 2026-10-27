import unittest
from dataclasses import replace
from research.volatility_compression_v1 import Config,STEP,backtest,indicators,signal,validate

def sample(n=850):
    out=[]; price=100.
    for i in range(n):
        spread=.01 if i<780 else .002
        close=price; out.append(dict(timestamp=i*STEP,open=close,high=close*(1+spread),low=close*(1-spread),close=close)); price=close
    out[799].update(open=100,high=103,low=99.9,close=102)
    for i in range(800,n):
        if i!=799: out[i].update(open=102,high=102.2,low=101.8,close=102)
    return out

class Tests(unittest.TestCase):
    def test_signal_and_next_open(self):
        b=sample(); a,n=indicators(b); s=signal(b,a,n,799); self.assertIsNotNone(s)
        t=backtest(b,0,len(b)*STEP); self.assertEqual(t[0]["entry_index"],800); self.assertEqual(t[0]["signal_index"],799)
    def test_prefix_invariance(self):
        b=sample(); a,n=indicators(b); s1=signal(b,a,n,799); b[830]["high"]=999; a2,n2=indicators(b); s2=signal(b,a2,n2,799); self.assertEqual(s1,s2)
    def test_missing_history_suppresses(self):
        b=sample(); b[400]["timestamp"]+=STEP; b.pop(401); a,n=indicators(b); self.assertIsNone(signal(b,a,n,798))
    def test_time_exit_and_no_overlap(self):
        t=backtest(sample(900),0,900*STEP); self.assertEqual(t[0]["reason"],"TIME"); self.assertEqual(t[0]["exit_index"]-t[0]["entry_index"]+1,72); self.assertTrue(all(x["exit_index"]<y["entry_index"] for x,y in zip(t,t[1:])))
    def test_stop_before_target(self):
        b=sample(); b[800].update(open=102,high=110,low=90,close=102); t=backtest(b,0,len(b)*STEP); self.assertEqual(t[0]["reason"],"STOP")
    def test_gap_stop(self):
        b=sample(); b[801].update(open=90,high=91,low=89,close=90); t=backtest(b,0,len(b)*STEP); self.assertEqual(t[0]["reason"],"GAP_STOP"); self.assertAlmostEqual(t[0]["raw_exit"],90)
    def test_cost_stress_and_sizing(self):
        b=sample(); base=backtest(b,0,len(b)*STEP)[0]; stress=backtest(b,0,len(b)*STEP,replace(Config(),fee=.0019,slippage=.0004))[0]; self.assertLess(stress["pnl"],base["pnl"]); self.assertLessEqual(base["qty"]*base["entry"],2000.000001); self.assertLessEqual(base["qty"]*(base["entry"]-base["stop"]),50.000001)
    def test_data_gap_exit(self):
        b=sample(); b[820]["timestamp"]+=STEP; b.pop(821); t=backtest(b,0,len(b)*STEP); self.assertEqual(t[0]["reason"],"DATA_GAP")
    def test_invalid(self):
        b=sample(); b[1]["low"]=101; self.assertRaises(ValueError,validate,b)

if __name__=="__main__": unittest.main()
