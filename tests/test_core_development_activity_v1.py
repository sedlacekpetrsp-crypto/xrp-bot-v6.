import unittest
from dataclasses import replace
from research.core_development_activity_v1 import Config,DAY,backtest,daily_signals

def prices(n=70,p=100.0):
    return [dict(timestamp=i*DAY,open=p,high=p+1,low=p-1,close=p) for i in range(n)]

class CoreDevelopmentTests(unittest.TestCase):
    def test_counts_and_prefix_invariance(self):
        events=sorted([10*DAY+1,11*DAY+2,12*DAY+3,13*DAY+4,14*DAY+5]+[i*DAY+6 for i in range(20,30)])
        full=daily_signals(events,0,40*DAY); prefix=daily_signals([x for x in events if x<25*DAY],0,25*DAY)
        self.assertEqual(prefix,{k:v for k,v in full.items() if k<=25*DAY})
        self.assertTrue(any(v['merge_count_7']>=5 and v['merge_count_30']>=15 for v in full.values()))

    def test_distinct_events_may_share_public_merge_second(self):
        events=[10*DAY+1]*15
        out=daily_signals(events,0,12*DAY)
        self.assertEqual(out[11*DAY]['merge_count_7'],15)

    def test_next_day_costs_sizing_and_overlap(self):
        rows=prices(); sig=dict(signal_day=19*DAY,merge_count_7=5,merge_count_30=15)
        rows[20]['development_signal']=sig; rows[21]['development_signal']=dict(sig,signal_day=20*DAY); rows[31]['development_signal']=dict(sig,signal_day=30*DAY)
        trades,_=backtest(rows,0,100*DAY)
        self.assertEqual(len(trades),2);self.assertAlmostEqual(trades[0]['entry'],100.02)
        self.assertLessEqual(trades[0]['leg_notional'],2000.000001);self.assertGreater(trades[1]['entry_timestamp'],trades[0]['exit_timestamp'])

    def test_ambiguous_stop_wins(self):
        rows=prices();rows[20]['development_signal']=dict(signal_day=19*DAY,merge_count_7=5,merge_count_30=15);rows[20].update(high=110,low=90)
        self.assertEqual(backtest(rows,0,100*DAY)[0][0]['reason'],'STOP')

    def test_gap_stop_worse_open(self):
        rows=prices();rows[20]['development_signal']=dict(signal_day=19*DAY,merge_count_7=5,merge_count_30=15);rows[21].update(open=90,high=91,low=89,close=90)
        t=backtest(rows,0,100*DAY)[0][0];self.assertEqual((t['reason'],t['raw_exit']),('GAP_STOP',90))

    def test_double_cost_hurts(self):
        rows=prices();rows[20]['development_signal']=dict(signal_day=19*DAY,merge_count_7=5,merge_count_30=15)
        a=backtest(rows,0,100*DAY)[0][0];b=backtest(rows,0,100*DAY,replace(Config(),fee=.0019,slippage=.0004))[0][0]
        self.assertLess(b['pnl'],a['pnl'])

    def test_gap_blocks_atr(self):
        rows=prices();del rows[15]; next(x for x in rows if x['timestamp']==20*DAY)['development_signal']=dict(signal_day=19*DAY,merge_count_7=5,merge_count_30=15)
        self.assertEqual(backtest(rows,0,100*DAY)[0],[])

if __name__=='__main__':unittest.main()
