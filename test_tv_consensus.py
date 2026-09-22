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

    def open(self, side, counter=False):
        row = dict(signal=side, candle_time=123, atr1=.002, score=80,
                   opposing_score=20, score_accel=3, trend_15m=side, countertrend=counter)
        self.assertTrue(tv.open_trade(row, 1.5))
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
            self.assertAlmostEqual(tv.net_pnl_for_exit(p, p['tp'])[-1], p['risk_dollars'] * 1.25)

    def test_countertrend_half_size_and_duplicate_candle(self):
        p = self.open('LONG', True)
        self.assertLessEqual(p['notional'], 1250.00001)
        tv.state['open_position'] = None
        self.assertFalse(tv.open_trade(dict(signal='SHORT', candle_time=123), 1.5))

    def test_break_even_covers_costs_and_stop_never_retreats(self):
        for side in ('LONG', 'SHORT'):
            tv.state.update(open_position=None, last_entry_candle=None)
            p = self.open(side)
            self.manage(self.price_at_r(p, .8))
            self.assertAlmostEqual(tv.net_pnl_for_exit(p, p['stop'])[-1], 0., places=7)
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
        self.manage(self.price_at_r(p, .5), dict(long_score=80, short_score=20))
        self.assertIsNotNone(tv.state['open_position'])

    def test_stale_loser_still_exits(self):
        p = self.open('SHORT')
        p['opened_at'] = (self.now-timedelta(minutes=50)).isoformat()
        self.manage(self.price_at_r(p, -.2), dict(long_score=20, short_score=80))
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


if __name__ == '__main__':
    unittest.main()
