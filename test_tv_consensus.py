"""Risk/exit regression scenarios. These are NOT a profitability backtest."""
import asyncio
import copy
import unittest
from datetime import timedelta
from unittest.mock import patch, AsyncMock

import app_v8 as base
import tv_consensus_scalper as tv


class RiskTests(unittest.TestCase):
    def setUp(self):
        self.now = tv.utcnow()
        state = copy.deepcopy(tv.state)
        state.update(balance=10000., equity=10000., open_position=None, trades=[],
                     cooldown_until=None, last_entry_candle=None)
        for name, value in [('state', state), ('base', base), ('save_state', lambda: None),
                            ('save_trade', lambda t: None), ('utcnow', lambda: self.now)]:
            p = patch.object(tv, name, value)
            p.start()
            self.addCleanup(p.stop)

    def row(self, side, counter=False):
        return dict(signal=side, candle_time=int(self.now.timestamp()//60*60000)-60000, atr1=.002, atr5=.006,
                   closed_price=1.5, swing_low=1.496, swing_high=1.504,
                   fast_long=True, fast_short=True, long_score=80 if side=="LONG" else 20,
                   short_score=80 if side=="SHORT" else 20, adx5=25, volume_ratio=1.5,
                   setup_long="TREND_PULLBACK", setup_short="TREND_PULLBACK", score=80,
                   opposing_score=20, score_accel=3, trend_15m=side, countertrend=counter)

    def open(self, side, counter=False):
        self.assertTrue(tv.open_trade(self.row(side, counter), 1.5))
        return tv.state['open_position']

    def manage(self, price, analysis=None):
        with patch.object(base, 'get_live_price', new=AsyncMock(return_value=price)):
            asyncio.run(tv.manage_position(analysis))

    def price_at_r(self, p, r):
        return base.target_market_for_net_profit(p['side'], p['entry'],
                                                p['risk_dollars'] * r / p['qty'])

    def test_long_short_risk_and_net_target(self):
        for side in ('LONG', 'SHORT'):
            tv.state.update(open_position=None, last_entry_candle=None)
            p = self.open(side)
            self.assertLessEqual(p['risk_dollars'], 15.000001)
            self.assertAlmostEqual(tv.net_pnl_for_exit(p, p['stop'])[-1], -p['risk_dollars'])
            self.assertAlmostEqual(tv.net_pnl_for_exit(p, p['tp'])[-1], p['risk_dollars'] * tv.NET_RR)

    def test_countertrend_and_neutral_forbidden(self):
        for side in ('LONG', 'SHORT'):
            for trend in ('NEUTRAL', 'SHORT' if side == 'LONG' else 'LONG'):
                self.assertFalse(tv.open_trade(dict(signal=side, candle_time=123, trend_15m=trend), 1.5))
        self.assertFalse(tv.open_trade(dict(signal='LONG', candle_time=123, trend_15m='LONG', countertrend=True), 1.5))

    def test_duplicate_candle_blocked(self):
        p = self.open('LONG')
        tv.state['open_position'] = None
        self.assertFalse(tv.open_trade(dict(signal='SHORT', candle_time=p['candle_time']), 1.5))

    def test_break_even_covers_costs_and_stop_never_retreats(self):
        for side in ('LONG', 'SHORT'):
            tv.state.update(open_position=None, last_entry_candle=None)
            p = self.open(side)
            self.manage(self.price_at_r(p, .8))
            self.assertAlmostEqual(tv.net_pnl_for_exit(p, p['stop'])[-1], tv.MIN_LOCKED_NET_R*p['risk_dollars'], places=7)
            stop = p['stop']
            self.manage(self.price_at_r(p, .5))
            self.assertEqual(p['stop'], stop)

    def test_trailing_locks_profit_on_reversal_both_sides(self):
        for side in ('LONG', 'SHORT'):
            tv.state.update(open_position=None, last_entry_candle=None)
            p = self.open(side)
            self.manage(self.price_at_r(p, 1.1))
            self.assertAlmostEqual(tv.net_pnl_for_exit(p, p['stop'])[-1], .6*p['risk_dollars'])
            self.manage(self.price_at_r(p, .5))
            self.assertIsNone(tv.state['open_position'])
            self.assertGreater(tv.state['trades'][-1]['net_pnl'], 0)

    def test_profitable_trend_survives_45_minutes(self):
        p = self.open('LONG')
        p['opened_at'] = (self.now-timedelta(minutes=50)).isoformat()
        self.manage(self.price_at_r(p, .5), dict(long_score=80, short_score=20, trend_15m='LONG'))
        self.assertIsNotNone(tv.state['open_position'])

    def test_stale_loser_still_exits(self):
        p = self.open('SHORT')
        p['opened_at'] = (self.now-timedelta(minutes=50)).isoformat()
        self.manage(self.price_at_r(p, -.2), dict(long_score=20, short_score=80, trend_15m='NEUTRAL'))
        self.assertIsNone(tv.state['open_position'])
        self.assertEqual(tv.state['trades'][-1]['reason'], 'TV STALE TRADE')

    def test_stop_processed_even_if_indicators_fail(self):
        p = self.open('LONG')
        with patch.object(base, 'get_live_price', new=AsyncMock(return_value=p['stop']*.999)), \
             patch.object(tv, 'analyze_market', new=AsyncMock(side_effect=RuntimeError('data down'))):
            with self.assertRaises(RuntimeError):
                asyncio.run(tv.cycle())
        self.assertIsNone(tv.state['open_position'])
        self.assertLess(tv.state['trades'][-1]['net_pnl'], 0)

    def test_loss_pause_expires_with_persisted_history(self):
        tv.state['trades'] = [dict(net_pnl=-1, closed_at=self.now.isoformat()) for _ in range(4)]
        self.assertTrue(tv.loss_streak_pause_active())
        self.now += timedelta(minutes=21)
        self.assertFalse(tv.loss_streak_pause_active())
        # History is preserved, and a new loss starts a fresh pause.
        tv.state['trades'].append(dict(net_pnl=-1, closed_at=self.now.isoformat()))
        self.assertTrue(tv.loss_streak_pause_active())

    def test_daily_loss_guard_still_blocks_after_pause(self):
        tv.state['trades'] = [dict(net_pnl=-30, closed_at=(self.now-timedelta(minutes=30)).isoformat()) for _ in range(4)]
        with patch.object(tv, 'analyze_market', new=AsyncMock(return_value={'signal':'LONG'})), \
             patch.object(base, 'get_live_price', new=AsyncMock()) as price:
            asyncio.run(tv.cycle())
        self.assertEqual(tv.state['status'], 'daily_loss_guard')
        price.assert_not_called()


    def test_high_score_cannot_bypass_momentum_or_setup(self):
        for change in ({'fast_long':False}, {'setup_long':None}, {'adx5':None}, {'adx5':float('nan')}):
            row=self.row('LONG'); row.update(long_score=100, **change)
            self.assertTrue(tv.entry_blockers(row,'LONG'))
            self.assertFalse(tv.open_trade(row,1.5))

    def test_structural_stop_rejects_excessive_distance_and_price_chase(self):
        for change,price in (({'swing_low':1.45},1.5), ({'atr5':.02},1.5), ({},1.51), ({},1.49), ({'atr1':float('nan')},1.5)):
            row=self.row('LONG'); row.update(change)
            self.assertFalse(tv.open_trade(row,price))
        self.assertIsNone(tv.state['open_position'])

    def test_old_signal_rejected(self):
        row=self.row('LONG'); row['candle_time']-=300000
        self.assertFalse(tv.open_trade(row,1.5))

    def test_wider_stop_reduces_size_and_respects_remaining_daily_budget(self):
        tv.state['trades']=[dict(net_pnl=-75,closed_at=self.now.isoformat())]
        p=self.open('LONG')
        self.assertLessEqual(p['risk_dollars'],5.00001)
        self.assertGreaterEqual(abs(p['entry']-p['stop']), .006-1e-8)
        self.assertGreaterEqual(tv.net_pnl_for_exit(p,p['tp'])[-1],1.5*p['risk_dollars']-1e-8)

    def test_flip_needs_two_distinct_candles_and_opposite_trend(self):
        p=self.open('LONG'); p['opened_at']=(self.now-timedelta(minutes=5)).isoformat()
        row=dict(long_score=20,short_score=90,trend_15m='LONG',candle_time=10)
        self.manage(self.price_at_r(p,-.1),row)
        self.assertIsNotNone(tv.state['open_position'])
        row.update(trend_15m='SHORT',candle_time=11)
        self.manage(self.price_at_r(p,-.1),row)
        self.manage(self.price_at_r(p,-.1),row)
        self.assertIsNotNone(tv.state['open_position'])
        row['candle_time']=12
        self.manage(self.price_at_r(p,-.1),row)
        self.assertIsNone(tv.state['open_position'])

    def test_stop_gap_is_recorded_honestly(self):
        p=self.open('LONG')
        self.manage(self.price_at_r(p,.8))
        price=self.price_at_r(p,-.2)
        expected=tv.net_pnl_for_exit(p,price)[-1]
        self.manage(price)
        self.assertAlmostEqual(tv.state['trades'][-1]['net_pnl'],expected)
        self.assertLess(expected,0)

    def test_price_guard_exits_while_analysis_is_blocked(self):
        p=self.open('LONG')
        async def run():
            started=asyncio.Event(); never=asyncio.Event()
            async def blocked():
                started.set(); await never.wait()
            with patch.object(tv,'analyze_market',new=blocked), patch.object(base,'get_live_price',new=AsyncMock(return_value=p['stop']*.999)):
                analysis=asyncio.create_task(tv.analyze_market())
                await started.wait()
                guard=asyncio.create_task(tv.price_guard_loop())
                for _ in range(20):
                    if tv.state['open_position'] is None: break
                    await asyncio.sleep(.001)
                self.assertIsNone(tv.state['open_position'])
                self.assertFalse(analysis.done())
                guard.cancel(); analysis.cancel()
                await asyncio.gather(guard,analysis,return_exceptions=True)
        asyncio.run(run())

    def test_pullback_and_breakout_setups_both_sides(self):
        for side in ('LONG','SHORT'):
            d=1 if side=='LONG' else -1
            for kind in ('TREND_PULLBACK','TREND_BREAKOUT'):
                closes=[1.5]*25 + ([1.5-d*.002,1.5+d*.001] if kind=='TREND_PULLBACK' else [1.5,1.5+d*.002])
                candles=[[i*60000,c-d*.0002,c+.0003,c-.0003,c,100] for i,c in enumerate(closes)]
                self.assertEqual(tv.entry_setup(side,candles,.003),kind)
            candles[-1][4]=1.5+d*.03
            self.assertIsNone(tv.entry_setup(side,candles,.003))


if __name__ == '__main__':
    unittest.main()
