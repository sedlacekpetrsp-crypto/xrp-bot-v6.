import contextlib,io,json,math,unittest
from datetime import datetime,timezone
from unittest.mock import patch
from research.best_validation import replay as r

class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.saved={k:getattr(r.c,k) for k in ('PAPER_BALANCE','positions','trade_history','cooldown_until','last_entry_candle','save_state','save_trade','utcnow','SLIPPAGE_RATE')}
        r.reset();r.c.save_trade=lambda t:None;r.c.utcnow=lambda:datetime(2026,1,1,tzinfo=timezone.utc);r.c.SLIPPAGE_RATE=.0002
    def tearDown(self):
        for k,v in self.saved.items():setattr(r.c,k,v)
    def a(self):return dict(signal='LONG',setup='BREAKOUT',signal_low=99.7,signal_high=100.1,candle_time=1)
    def open(self,s='XRPUSDT',a=None):
        with contextlib.redirect_stdout(io.StringIO()):return r.c.open_trade(s,a or self.a(),100)
    def test_position_limit_and_duplicate(self):
        self.assertTrue(self.open());self.assertFalse(self.open());self.assertTrue(self.open('BTCUSDT'));self.assertFalse(self.open('SOLUSDT'))
    def test_structural_stop_keeps_cash_risk(self):
        self.open();p=r.c.positions['XRPUSDT'];qty=p['qty'];risk=p['risk_usdt']
        r.reset();a=self.a();a['signal_low']=99.;self.open(a=a);p=r.c.positions['XRPUSDT']
        self.assertLess(p['qty'],qty);self.assertLessEqual(p['risk_usdt'],risk+1e-8);self.assertLessEqual(p['risk_usdt'],15.)
    def test_costs_counted_once_and_duplicate_close_noop(self):
        self.open();p=r.c.positions['XRPUSDT'];expected=r.c.estimated_net_per_unit('LONG',p['entry_price'],101)*p['qty']
        with contextlib.redirect_stdout(io.StringIO()):r.c.close_trade('XRPUSDT',101,'TEST');r.c.close_trade('XRPUSDT',101,'TEST')
        self.assertAlmostEqual(r.c.PAPER_BALANCE,10000+expected);self.assertEqual(len(r.c.trade_history),1)
    def test_ambiguous_bar_stop_first_and_gap(self):
        p=dict(side='LONG',stop_loss=99,take_profit=102,breakeven_moved=False)
        self.assertEqual(r.bar_exit(p,[0,100,103,98,101]),(99,'STOP LOSS'))
        self.assertEqual(r.bar_exit(p,[0,97,103,96,101]),(97,'STOP LOSS'))
        p.update(side='SHORT',stop_loss=102,take_profit=99)
        self.assertEqual(r.bar_exit(p,[0,103,104,98,100]),(103,'STOP LOSS'))
    def test_invalid_gap_and_duplicate_data(self):
        good=[[0,100,101,99,100,10,299999],[300000,100,101,99,100,10,599999]]
        r.validate(good)
        for bad in ([good[0],good[0]],[good[0],[600000,100,101,99,100,10,899999]],[[0,100,float('nan'),99,100,10,299999]]):
            with self.assertRaises(ValueError):r.validate(bad)
    def test_no_future_candle_changes_past_signals(self):
        rows=[[i*r.STEP,100+i*.01,101+i*.01,99+i*.01,100.5+i*.01,10,(i+1)*r.STEP-1] for i in range(1350)]
        rows[1250]=[1250*r.STEP,112.49,113.32,112.47,113.3,30,1251*r.STEP-1]
        with contextlib.redirect_stdout(io.StringIO()):a=r.prepare({'XRPUSDT':rows[:1300]});b=r.prepare({'XRPUSDT':rows})
        self.assertTrue(a['XRPUSDT'])
        self.assertEqual(a['XRPUSDT'],{i:v for i,v in b['XRPUSDT'].items() if i<1300})
    def test_known_defect_legacy_respects_portfolio_entry_denial(self):
        with patch.object(r.c,'portfolio_entry_allowed',return_value=(False,'TEST_DENY'),create=True):
            self.assertFalse(self.open())
    def test_known_defect_legacy_respects_portfolio_risk_allowance(self):
        with patch.object(r.c,'portfolio_risk_allowance',return_value=(1.,{}),create=True):
            self.assertTrue(self.open())
            self.assertLessEqual(r.c.positions['XRPUSDT']['risk_usdt'],1.)
    def test_aggregation_only_complete_bars(self):
        rows=[[i*r.STEP,100,101,99,100,10,(i+1)*r.STEP-1] for i in range(4)]
        self.assertEqual(len(r.aggregate(rows,3)),1);self.assertEqual(r.aggregate(rows,3)[0][6],899999)

if __name__=='__main__':unittest.main()
