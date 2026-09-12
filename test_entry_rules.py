import copy
import time
import unittest
from unittest.mock import patch
import entry_rules as rules
import app_v8_candle as fixed
import v8_candle_scanner_engine as scanner

class EntryTests(unittest.TestCase):
    def signal(self, side='LONG'):
        return dict(side=side, setup='MOMENTUM_BREAKOUT', score=6, symbol='XRPUSDT', entry=100., trigger_level=99.95 if side=='LONG' else 100.05, pattern_low=99., pattern_high=101., candle_time=int(time.time()*1000)-70000, reasons=[])

    def test_guards_both_directions(self):
        for side in ['LONG','SHORT']:
            s=self.signal(side)
            self.assertIsNone(rules.rejection(s,100.))
            for px in [100.2,99.8,0,float('nan')]:
                self.assertIsNotNone(rules.rejection(s,px))
            self.assertIsNotNone(rules.rejection(s,99.94 if side=='LONG' else 100.06))
            s['candle_time']-=100000
            self.assertIsNotNone(rules.rejection(s,100.))
            s['candle_time']=int(time.time()*1000)
            self.assertIsNotNone(rules.rejection(s,100.))

    def test_actual_execution_price_costs_and_risk(self):
        for engine in [fixed,scanner]:
            for side in ['LONG','SHORT']:
                engine.paper_position=None
                sig=self.signal(side)
                market=100.1 if side=='LONG' else 99.9
                with patch.object(engine,'save_state'):
                    self.assertTrue(engine.open_position(sig,market))
                p=engine.paper_position
                self.assertAlmostEqual(p['entry_price'],market*(1.0002 if side=='LONG' else .9998))
                self.assertEqual(p['signal_price'],100.)
                self.assertLessEqual(p['qty']*p['entry_price'],engine.paper_balance*engine.MAX_NOTIONAL_SHARE+1e-8)
                net=engine.estimated_net_per_unit if engine is fixed else engine.est_net_unit
                loss=-net(side,p['entry_price'],p['stop_loss'])*p['qty']
                profit=net(side,p['entry_price'],p['take_profit'])*p['qty']
                self.assertAlmostEqual(profit,2*loss,places=7)
                engine.paper_position=None
                with patch.object(engine,'save_state') as save:
                    self.assertFalse(engine.open_position(self.signal(side),102.))
                    save.assert_not_called()
                self.assertIsNone(engine.paper_position)

    def test_existing_position_exit_works_without_new_fields(self):
        fixed.paper_position=dict(side='LONG',entry_price=100.,qty=1.,stop_loss=99.,take_profit=102.,entry_time='2026-01-01T00:00:00+00:00',risk_usdt=1.)
        with patch.object(fixed,'close_position') as close:
            fixed.manage_position(98.)
            self.assertEqual(close.call_args_list[0].args,(98.,'STOP_LOSS'))
        fixed.paper_position=None

    def test_intervals(self):
        self.assertEqual(fixed.MAIN_INTERVAL,'1m')
        self.assertEqual(fixed.STRUCTURE_INTERVAL,'15m')
        self.assertEqual(scanner.ENTRY_INTERVAL,'1m')
        self.assertEqual(fixed.TRADING_MODE,'PAPER')

if __name__=='__main__':unittest.main()
