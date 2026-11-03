import unittest
from types import SimpleNamespace
from test_exit_regressions import functions
import paper_overlap_guard as guard
from research.paper_overlap_20261018.audit import audit

class CandidateTests(unittest.TestCase):
    def test_quote_alias_and_opposite_side(self):
        for side in ('LONG','SHORT'):
            self.assertEqual(guard.entry_allowed('XRPUSDC',side,[{'symbol':'XRPUSDT','side':'LONG'}]),(False,'ASSET_ALREADY_OPEN'))
        self.assertTrue(guard.entry_allowed('ETHUSDC','LONG',[{'symbol':'XRPUSDT'}])[0])
    def test_unknown_exposure_fails_closed(self):
        self.assertFalse(guard.entry_allowed('XRPUSDC','LONG',[{}])[0])
        self.assertFalse(guard.entry_allowed('','LONG',[])[0])
    def test_real_fly_position_and_pause(self):
        env=dict(PAUSED_BOTS={'FLY','FAST','LEADLAG','TV'},paper_overlap_guard=guard,
                 base=SimpleNamespace(paper_position={'symbol':'XRPUSDC'}),
                 fast=SimpleNamespace(state={}),leadlag=SimpleNamespace(state={},TRADE_SYMBOL='XRPUSDC'),
                 tv=SimpleNamespace(state={}),whale=SimpleNamespace(state={}))
        f=functions('app_v8_fly.py',{'portfolio_entry_allowed'},env)['portfolio_entry_allowed']
        self.assertEqual(f('FLY','ETHUSDC','LONG'),(False,'USER_PAUSED'))
        self.assertFalse(f('WHALE','XRPUSDT','SHORT')[0])
        self.assertTrue(f('WHALE','ETHUSDT','SHORT')[0])
        self.assertTrue(f('BEST','XRPUSDT','LONG')[0])
    def test_half_open_intervals_and_duplicate_rejection(self):
        a=dict(bot='FLY',id='1',symbol='XRPUSDC',side='LONG',opened_at='2026-10-01T00:00:00Z',closed_at='2026-10-01T01:00:00Z',net_pnl=-1,fees=1)
        b=dict(a,bot='TV',opened_at=a['closed_at'],closed_at='2026-10-01T02:00:00Z')
        self.assertEqual(audit([a,b])['pairs'],{})
        with self.assertRaises(ValueError):audit([a,a])
        b['opened_at']='2026-10-01T00:30:00Z'
        self.assertEqual(audit([a,b])['pairs']['FLY / TV']['same_asset'],1)
    def test_fast_atr_cannot_manufacture_edge(self):
        import fast_scalper as f
        f.base=SimpleNamespace(ROUND_TRIP_COST=.0023)
        row=dict(symbol='XRPUSDC',regime='RANGE',volume_ratio=5,adx5=10,z_momentum=-2.5,rsi=30,book_imbalance=.8,real_spread_pct=.0001,expected_move_pct=.0001,atr=.01,price=1)
        self.assertIn('EDGE',f._fast_signal(row)['fast_blockers'])
    def test_fly_exhaustion_rejected(self):
        env=dict(m=SimpleNamespace(ROUND_TRIP_COST=.002,MIN_EDGE_MULTIPLE=1),_no_trade_reason=lambda a:None)
        f=functions('v8_fly_layer.py',{'entry_blocker'},env)['entry_blocker']
        for z in (3.1,-3.1,float('nan')):
            self.assertEqual(f(dict(signal='LONG',expected_move_pct=.01,z_momentum=z)),'OVEREXTENDED_MOMENTUM')

class HourFilterTests(unittest.TestCase):
    def test_only_closed_hours_used(self):
        import bisect
        rows=[[i*3600000,0,0,0,100+i,0,(i+1)*3600000-1] for i in range(60)]
        env=dict(hour_bars=rows,hour_ends=[r[6] for r in rows],bisect=bisect,
                 base=SimpleNamespace(ema=lambda closes,n:sum(closes[-n:])/n))
        f=functions('research/paper_overlap_20261018/run_tv.py',{'hourly_aligned'},env)['hourly_aligned']
        now=50*3600000
        self.assertTrue(f(now,'LONG'))
        rows[50][4]=-999999
        self.assertTrue(f(now,'LONG'))
        self.assertFalse(f(now,'SHORT'))
        self.assertFalse(f(49*3600000,'LONG'))

if __name__=='__main__': unittest.main()
