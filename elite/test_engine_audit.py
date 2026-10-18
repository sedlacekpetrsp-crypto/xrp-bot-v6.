"""Hand cashbook fixtures and rejection tests, independent of strategy outcomes."""
from decimal import Decimal as D
from types import SimpleNamespace
import unittest
from elite.research_engine import Decision,simulate

class EngineAuditTests(unittest.TestCase):
    def rows(self):return [(i*300000,100.,100.,100.,100.) for i in range(4)]

    def test_fee_only_target_against_decimal_cashbook(self):
        # Buy100, stop90, target110,1% fee. Loss/unit=101-89.1=11.9.
        # Risk50 buys50/11.9 units; net/unit=108.9-101=7.9.
        rows=self.rows();rows[2]=(600000,100.,110.,100.,110.)
        result=simulate(rows,{0:Decision(10,10)},fee=.01,slip=0,half_spread=0)
        qty=D(50)/D('11.9');expected=qty*D('7.9')
        self.assertEqual(result['trade_log'][0]['reason'],'TARGET')
        self.assertAlmostEqual(result['net_pnl'],float(expected),places=9)
        self.assertAlmostEqual(result['costs'],float(qty*D('2.1')),places=9)

    def test_allocation_cap_with_large_gap_risk(self):
        # Tight stop would risk-size500 units;35% cash cap buys35 instead.
        rows=self.rows();rows[2]=(600000,80.,80.,80.,80.)
        r=simulate(rows,{0:Decision(.1)},fee=0,slip=0,half_spread=0)
        self.assertAlmostEqual(r['net_pnl'],-700)
        self.assertEqual(r['trade_log'][0]['reason'],'STOP_GAP')

    def test_slip_spread_and_fees_on_both_sides(self):
        # Entry100*(1+.002+.001)=100.3; exit100*(1-.003)=99.7.
        # Stop80.3 exits adversely80.0591; fees .1% each side.
        qty=D(50)/(D('100.3')*D('1.001')-D('80.3')*D('.997')*D('.999'))
        expected=qty*(D('99.7')*D('.999')-D('100.3')*D('1.001'))
        r=simulate(self.rows(),{0:Decision(20)},fee=.001,slip=.002,half_spread=.001)
        self.assertAlmostEqual(r['net_pnl'],float(expected),places=9)
        self.assertAlmostEqual(r['net_pnl'],-r['costs'],places=9)

    def test_target_gap_is_conservative_and_no_same_bar_reentry(self):
        rows=self.rows();rows[2]=(600000,120.,125.,115.,120.)
        r=simulate(rows,{0:Decision(10,10),1:Decision(10,10)},fee=0,slip=0,half_spread=0)
        self.assertEqual(r['trades'],1)
        self.assertEqual(r['trade_log'][0]['reason'],'TARGET_GAP')
        self.assertAlmostEqual(r['net_pnl'],50)

    def test_time_exit_and_signal_causality(self):
        rows=self.rows();rows[2]=(600000,110.,110.,110.,110.)
        r=simulate(rows,{0:Decision(20,max_bars=1)},fee=0,slip=0,half_spread=0)
        self.assertEqual(r['trade_log'][0]['entry_index'],1)
        self.assertEqual(r['trade_log'][0]['exit_index'],2)
        self.assertEqual(r['trade_log'][0]['reason'],'TIME')
        self.assertAlmostEqual(r['net_pnl'],25)
        self.assertEqual(simulate(rows,{3:Decision(20)})['trades'],0)

    def test_open_position_close_drawdown_and_daily_liquidation(self):
        rows=[(0,100.,100.,100.,100.),(300000,100.,120.,100.,120.),
              (600000,120.,120.,90.,90.),(900000,90.,100.,90.,100.)]
        r=simulate(rows,{0:Decision(20)},fee=0,slip=0,half_spread=0)
        self.assertAlmostEqual(r['close_mtm_drawdown_pct'],75/10050*100)
        self.assertEqual(r['net_pnl'],0)
        self.assertEqual(r['daily_equity'],{0:10000})

    def test_simulator_rejects_invalid_market_data_directly(self):
        for rows in ([(0,100.,99.,98.,100.)],[(0,100.,float('nan'),99.,100.)],
                     [(0,100.,100.,100.,100.),(600000,100.,100.,100.,100.)]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):simulate(rows,{})

    def test_rejects_nonfinite_negative_and_fractional_instructions(self):
        bad=[Decision(float('nan')),Decision(float('inf')),Decision(-1),
             Decision(1,float('nan')),Decision(1,-2),Decision(1,max_bars=-1),
             Decision(1,max_bars=.5),Decision(1,exit='yes'),
             SimpleNamespace(stop_distance=1,target_distance=0,exit=False,max_bars=0,trail_distance=-1)]
        for d in bad:
            with self.subTest(decision=d), self.assertRaises(ValueError):simulate(self.rows(),{0:d})
