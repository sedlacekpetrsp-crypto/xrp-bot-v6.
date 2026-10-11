import unittest
from unittest.mock import patch
from research.best_validation import replay as r

class ExitHypothesis(unittest.TestCase):
    def test_only_break_even_disabled_original_stop_and_target_remain(self):
        start=r.stamp('2026-07-04');step=r.STEP
        rows=[[start,100,100.75,99.8,100.7,10,start+step-1],
              [start+step,100.7,100.8,100.,100.5,10,start+2*step-1],
              [start+2*step,100.5,101,100.4,100.9,10,start+3*step-1]]
        a=dict(signal='LONG',setup='BREAKOUT',signal_low=99.7,signal_high=100.1,candle_time=start-step)
        keys=('PAPER_BALANCE','positions','trade_history','cooldown_until','last_entry_candle','save_state','save_trade','utcnow','SLIPPAGE_RATE')
        with patch.multiple(r.c,**{k:getattr(r.c,k) for k in keys}):
            _,base=r.simulate({'XRPUSDT':rows},{'XRPUSDT':{0:a}},'baseline','2026-07-04','2026-07-05')
            _,alt=r.simulate({'XRPUSDT':rows},{'XRPUSDT':{0:a}},'no_breakeven','2026-07-04','2026-07-05')
            self.assertEqual(base[0]['reason'],'BREAK EVEN')
            self.assertEqual(alt[0]['reason'],'TAKE PROFIT')
            self.assertEqual(base[0]['qty'],alt[0]['qty'])
            rows[1][3]=99
            _,stopped=r.simulate({'XRPUSDT':rows},{'XRPUSDT':{0:a}},'no_breakeven','2026-07-04','2026-07-05')
            self.assertEqual(stopped[0]['reason'],'STOP LOSS')
            self.assertLess(stopped[0]['pnl'],0)

if __name__=='__main__':unittest.main()
