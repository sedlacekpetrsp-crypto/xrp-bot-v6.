import unittest
from unittest.mock import patch
from elite.research_engine import Decision,simulate
from elite.exit_v21 import TrailingDecision,decisions

class ExitTests(unittest.TestCase):
    def run_rows(self,values,trail=10):
        rows=[(i*300000,*v) for i,v in enumerate(values)]
        return simulate(rows,{-1:TrailingDecision(10,trail_distance=trail)},fee=0,slip=0,half_spread=0)
    def test_close_not_high_and_next_bar(self):
        r=self.run_rows([(100,130,95,110),(110,112,101,105),(105,106,99,102)])
        self.assertEqual(r['trade_log'][0]['exit_index'],2)
        self.assertAlmostEqual(r['net_pnl'],0)
    def test_gap_worse_open(self):
        r=self.run_rows([(100,120,95,115),(100,105,99,102)])
        self.assertEqual(r['trade_log'][0]['reason'],'STOP_GAP')
        self.assertAlmostEqual(r['net_pnl'],0)
    def test_never_loosen(self):
        r=self.run_rows([(100,120,95,115),(115,116,106,110),(110,111,104,108)])
        self.assertAlmostEqual(r['net_pnl'],25)
    def test_no_trailing_legacy(self):
        r=self.run_rows([(100,130,95,110),(110,112,99,102)],0)
        self.assertEqual(r['trade_log'][0]['reason'],'BOUNDARY')
        self.assertAlmostEqual(r['net_pnl'],10)
    def test_entry_rules_and_btc_exit(self):
        bars=[(k*12+11,100,101,89,100 if k<200 else 90) for k in range(201)]
        original={2411:Decision(3,exit=False)}
        with patch('elite.exit_v21.original_decisions',return_value=original),patch('elite.exit_v21.aggregate',return_value=bars):
            for name in ('v21','v22','v23'):
                d=decisions([],[],name)[2411]
                self.assertEqual(d.stop_distance,3)
                self.assertEqual(d.exit,name!='v21')
                self.assertEqual(d.trail_distance,0 if name=='v22' else 3)

if __name__=='__main__':unittest.main()
