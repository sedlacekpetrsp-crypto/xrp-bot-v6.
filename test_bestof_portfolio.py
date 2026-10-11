import contextlib
import io
import unittest
from unittest.mock import patch
import bestof_bot as bot
from test_bestof_ema4h import core, signal
from test_bestof_ema4h_persistence import Connection
from bestof_portfolio import entry_budget

class Portfolio(unittest.TestCase):
    def test_hook_failure_invalid_or_enlarged_allowance(self):
        c=core()
        for result in (float('nan'),float('inf'),-1,0):
            c.portfolio_risk_allowance=lambda *args:(result,{})
            self.assertEqual(entry_budget(c,'XRPUSDT','LONG',10)[0],0)
        c.portfolio_risk_allowance=lambda *args:(1000,{})
        self.assertEqual(entry_budget(c,'XRPUSDT','LONG',10)[0],10)
        def failed(*args):raise RuntimeError('coordinator unavailable')
        c.portfolio_entry_allowed=failed
        self.assertEqual(entry_budget(c,'XRPUSDT','LONG',10),(0,0))
    def test_invalid_restored_position_blocks_entry(self):
        c=core();c.positions['ETHUSDT']={'qty':1,'entry_price':100}
        self.assertEqual(entry_budget(c,'XRPUSDT','LONG',10),(0,0))
    def test_ema_and_legacy_enforce_hooks(self):
        c=bot.core
        with patch.multiple(c,PAPER_BALANCE=10000.,positions={},last_entry_candle={},cooldown_until={},save_state=lambda:None):
            a=dict(signal='SHORT',setup='BREAKOUT',signal_low=99.9,signal_high=100.3,candle_time=1)
            with patch.object(c,'portfolio_entry_allowed',return_value=(False,'deny'),create=True):
                self.assertFalse(c.open_trade('SOLUSDT',a,100))
                self.assertEqual(c.positions,{})
                self.assertEqual(c.last_entry_candle,{})
        e=core();e.portfolio_entry_allowed=lambda *args:(False,'deny')
        self.assertFalse(bot.ema4h.open_ema(e,'XRPUSDT',signal(),100))
        e.portfolio_entry_allowed=lambda *args:(True,'ok')
        e.portfolio_risk_allowance=lambda *args:(1.,{})
        self.assertTrue(bot.ema4h.open_ema(e,'XRPUSDT',signal(),100))
        self.assertLessEqual(e.positions['XRPUSDT']['risk_usdt'],1.00000001)
    def test_restored_ema_risk_and_exposure_cap_legacy_entry(self):
        c=bot.core;db={'state':{},'trades':[]}
        old=dict(symbol='ETHUSDT',setup='EMA_4H',risk_usdt=29.,qty=65.,entry_price=100.)
        with patch.multiple(c,DATABASE_URL='test',get_db=lambda:Connection(db),PAPER_BALANCE=10000.,positions={'ETHUSDT':old},last_entry_candle={},cooldown_until={},trade_history=[]):
            c.save_state();c.positions={};c.load_state()
            a=dict(signal='LONG',setup='BREAKOUT',signal_low=99.7,signal_high=100.1,candle_time=1)
            self.assertTrue(c.open_trade('XRPUSDT',a,100))
            p=c.positions['XRPUSDT']
            self.assertLessEqual(p['risk_usdt'],1.00000001)
            self.assertLessEqual(p['qty']*p['entry_price'],500.00000001)
            self.assertFalse(c.open_trade('SOLUSDT',a,100))
    def test_strategy_stats_reconcile_and_empty_is_not_success(self):
        c=core();c.trade_history=[{'setup':'BREAKOUT','pnl':3,'fees':1},{'setup':'FIB_0618_0786','pnl':-2,'fees':.5}]
        g=bot.ema4h.summary(c)['strategy_groups']
        self.assertEqual([x['trades'] for x in g],[1,1,0])
        self.assertEqual(sum(x['net_pnl'] for x in g),1)
        self.assertIsNone(g[-1]['win_rate'])
        self.assertIsNone(g[-1]['pf'])

if __name__=='__main__':unittest.main()
