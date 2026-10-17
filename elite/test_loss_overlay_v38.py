import unittest
from elite.loss_overlay_v38 import LossOverlay,DAY
from elite.research_engine import Decision,simulate

class LossOverlayTests(unittest.TestCase):
    def rows(self,n=10):return [(i*300000,100,101,98,100) for i in range(n)]
    def overlay(self,n='v38'):
        rows=self.rows();return LossOverlay(rows,{i:Decision(1) for i in range(-1,10)},{},n)
    def test_trigger_after_third_fill_and_reset_between_runs(self):
        r=self.rows();s=self.overlay()
        a=simulate(r,s,fee=0,slip=0,half_spread=0)
        self.assertEqual(a['trades'],3)
        self.assertEqual(a['overlay_events'][0]['trigger_exit_index'],2)
        self.assertEqual(a['overlay_events'][0]['known_at'],900000)
        self.assertEqual(a,simulate(r,s,fee=0,slip=0,half_spread=0))
    def test_nonloss_breaks_streak(self):
        s=self.overlay()
        for pnl in (-1,-1,0,-1,-1):s.on_closed_trade(dict(pnl=pnl,exit_timestamp=0,exit_index=0))
        self.assertEqual(s.events,[])
    def test_expiry_and_exit_preserved(self):
        s=self.overlay();s.base[-1]=Decision(1,exit=True)
        for _ in range(3):s.on_closed_trade(dict(pnl=-1,exit_timestamp=0,exit_index=0))
        self.assertEqual(s.for_position(-1).stop_distance,0)
        self.assertTrue(s.for_position(-1).exit)
        s.times[0]=s.until
        self.assertEqual(s.for_position(-1).stop_distance,1)
    def test_stricter_entry_only_during_window(self):
        s=self.overlay('v39');s.strict[-1]=Decision(1)
        self.assertEqual(s.for_position(0).stop_distance,1)
        for _ in range(3):s.on_closed_trade(dict(pnl=-1,exit_timestamp=0,exit_index=0))
        self.assertEqual(s.for_position(-1).stop_distance,1)
        self.assertEqual(s.for_position(0).stop_distance,0)
    def test_prefix_decisions_do_not_see_future_losses(self):
        r=self.rows();a=simulate(r,self.overlay(),end=3,fee=0,slip=0,half_spread=0)
        b=simulate(r,self.overlay(),fee=0,slip=0,half_spread=0)
        self.assertEqual(a['trade_log'],b['trade_log'])
