import unittest
from dataclasses import replace
from research.aggressor_sell_burst_v1 import Config,MinuteBuilder,STEP,TS,VALID,backtest,signal

def make_bars(n=50):
    out=[]
    for i in range(n): out.append((i*STEP,100,100.1,99.9,100,100,80,25,True))
    out[0]=(0,100,100,99.7,99.7,100,80,25,True)
    return out

class Tests(unittest.TestCase):
    def test_tick_aggregation_side_and_run_reset(self):
        b=MinuteBuilder()
        for i,s in enumerate([True,True,False,True,True,True]): b.feed(i+1,1000+i,100-i*.01,s)
        bars=b.finish(); self.assertEqual(bars[0][5:8],(6,5,3))
    def test_run_resets_at_minute(self):
        b=MinuteBuilder(); b.feed(1,59_999,100,True); b.feed(2,60_000,99,True); x=b.finish(); self.assertEqual(x[0][7],1); self.assertEqual(x[1][7],1)
    def test_id_gap_invalidates_adjacent(self):
        b=MinuteBuilder(); b.feed(1,59_999,100,True); b.feed(3,60_000,99,True); x=b.finish(); self.assertFalse(x[0][VALID]); self.assertFalse(x[1][VALID]); self.assertEqual(b.id_gaps,1)
    def test_duplicate_id_rejected(self):
        b=MinuteBuilder(); b.feed(1,1,100,True); self.assertRaises(ValueError,b.feed,1,1,100,True)
    def test_signal_and_next_minute(self):
        x=make_bars(); self.assertIsNotNone(signal(x[0])); t=backtest(x,0,50*STEP); self.assertEqual(t[0]['entry_index'],1)
    def test_prefix_invariance(self):
        x=make_bars(); a=backtest(x,0,50*STEP)[0]; x[40]=(40*STEP,10,20,5,10,10,0,0,True); b=backtest(x,0,50*STEP)[0]; self.assertEqual((a['entry'],a['stop'],a['target']),(b['entry'],b['stop'],b['target']))
    def test_stop_first_and_gap(self):
        x=make_bars(); x[1]=(STEP,100,102,98,100,100,0,0,True); t=backtest(x,0,50*STEP); self.assertEqual(t[0]['reason'],'STOP')
        x=make_bars(); x[2]=(2*STEP,98,99,97,98,100,0,0,True); t=backtest(x,0,50*STEP); self.assertEqual(t[0]['reason'],'GAP_STOP')
    def test_nonoverlap_time(self):
        x=make_bars(100); t=backtest(x,0,100*STEP); self.assertTrue(all(a['exit_index']<b['entry_index'] for a,b in zip(t,t[1:])))
    def test_cost_stress_sizing(self):
        x=make_bars(); a=backtest(x,0,50*STEP)[0]; b=backtest(x,0,50*STEP,replace(Config(),fee=.0019,slippage=.0004))[0]; self.assertLess(b['pnl'],a['pnl']); self.assertLessEqual(a['qty']*a['entry'],2000.000001); self.assertLessEqual(a['qty']*(a['entry']-a['stop']),50.000001)
    def test_data_gap_exit(self):
        x=make_bars(); x.pop(3); t=backtest(x,0,51*STEP); self.assertEqual(t[0]['reason'],'DATA_GAP')

if __name__=='__main__': unittest.main()
