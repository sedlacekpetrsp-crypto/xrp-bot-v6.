"""Compare real entry paths with/without overlay; quantity and TP must match."""
import copy
import json
import unittest
from unittest.mock import patch
import paper_stop_policy as policy

class StopOverlay(unittest.TestCase):
    def compare(self, factory):
        with patch.object(policy,'MULTIPLIER',1.0): before=factory()
        with patch.object(policy,'MULTIPLIER',1.15): after=factory()
        self.assertTrue(before); self.assertTrue(after)
        entry=before.get('entry_price',before.get('entry'))
        key='stop_loss' if 'stop_loss' in before else 'stop'
        self.assertAlmostEqual(abs(entry-after[key]),1.15*abs(entry-before[key]))
        self.assertEqual(before['qty'],after['qty'])
        for k in ['take_profit','tp','risk_usdt','risk_dollars','risk_usdc','initial_risk_usdc','initial_risk_distance']:
            self.assertEqual(before.get(k),after.get(k),k)
        self.assertGreater(after['stop_loss_risk_net'],0)
        restored=json.loads(json.dumps(after))
        with patch.object(policy,'MULTIPLIER',1.15):policy.apply(restored)
        self.assertEqual(restored,after)
        return after

    def test_swing_both_sides_and_two_families(self):
        import swing_paper as s
        from test_swing_paper import ready,quote,frame,NOW
        for family in s.CONFIG:
            for side in (1,-1):
                self.compare(lambda:s.advance(ready(),family,quote(),frame(side),NOW)[0]['positions']['XRPUSDT'])

    def test_news_quantity_target_and_net_risk(self):
        import news_paper as n
        from test_news_paper import signal,KEY_NEWS,CONFIG,NOW
        p=self.compare(lambda:n.advance(n.initial(),dict(price=1.4,time=NOW),signal(),KEY_NEWS,NOW,CONFIG)['position'])
        self.assertAlmostEqual(p['stop_loss_risk_net'],-n.net(p,p['stop_loss'])[0])

    def test_lh_whale_both_sides(self):
        import lh_whale as lh
        def enter(side):
            s=lh.initial();s['activated_at']=1
            return lh.advance(s,dict(price=100,time=300010),dict(candle=300000,signal=side,stop=98 if side=='LONG' else 102),300010)['position']
        for side in ('LONG','SHORT'):
            p=self.compare(lambda:enter(side))
            self.assertAlmostEqual(p['stop_loss_risk_net'],-lh.net(p,p['stop_loss'])[0])

    def test_best_ema(self):
        from test_bestof_ema4h import core,signal
        import bestof_ema4h as e
        def enter():
            c=core();self.assertTrue(e.open_ema(c,'XRPUSDT',signal(),100));return c.positions['XRPUSDT']
        p=self.compare(enter)
        self.assertAlmostEqual(p['stop_loss_risk_net'],-e.net_per_unit(p,p['stop_loss'])*p['qty'])

    def test_best_breakout_both_sides(self):
        import app_bestof_core as c
        def enter(side):
            with patch.multiple(c,PAPER_BALANCE=10000.,positions={},last_entry_candle={},cooldown_until={},save_state=lambda:None):
                with patch.object(c,'portfolio_entry_allowed',return_value=(True,'ok'),create=True):
                    self.assertTrue(c.open_trade('XRPUSDT',dict(signal=side,setup='BREAKOUT',signal_low=99.7,signal_high=100.3,candle_time=1),100))
                return copy.deepcopy(c.positions['XRPUSDT'])
        for side in ('LONG','SHORT'): self.compare(lambda:enter(side))

    def test_whale_trendline_and_fib_both_sides(self):
        import app_blue_whale_mirror as w
        def enter(side,strategy):
            stop,tp=(96,110) if side=='LONG' else (104,90)
            state=copy.deepcopy(w.state)
            state.update(balance=10000.,open_positions=[],open_position=None,trades=[],seen_signal_ids=[],market_prices={'XRPUSDT':100})
            with patch.object(w,'state',state),patch.object(w,'save_state',lambda:None):
                with patch.object(w,'portfolio_entry_allowed',return_value=(True,'ok'),create=True):
                    ok=w.open_paper(dict(id=42,text=side,symbol='XRPUSDT',strategy=strategy,entry=100,tp=tp,stop=dict(low=stop,high=stop,raw=str(stop),masked=False)),side,100)
                    self.assertTrue(ok)
                    return copy.deepcopy(w.state['open_positions'][0])
        self.compare(lambda:enter('LONG',w.whale_trendline.STRATEGY))
        # FIB quality band is narrower than the 4h trendline band.
        with patch.object(w,'WHALE_MAX_STOP_RATE',.05):
            for side in ('LONG','SHORT'):self.compare(lambda:enter(side,'FIB_0618_0786'))

    def test_profit_stops_not_loosened_and_other_fields_unchanged(self):
        for side,stop in [('LONG',101),('SHORT',99)]:
            p=dict(side=side,entry=100,stop=stop,qty=2,tp=110);before=p.copy()
            with patch.object(policy,'MULTIPLIER',1.15):policy.apply(p)
            self.assertEqual(p,before)

if __name__=='__main__': unittest.main()
