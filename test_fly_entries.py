"""Entry regressions; synthetic candles are not a profitability backtest."""
import asyncio
import unittest
from unittest.mock import patch, AsyncMock
import app_v8 as base
import v8_fly_layer as fly

class EntryTests(unittest.TestCase):
    def setUp(self):
        fly.m = base
        self.history = patch.object(base, 'trade_history', [])
        self.history.start()
        self.addCleanup(self.history.stop)
        self.row = dict(symbol='XRPUSDC', signal='WAIT', raw_signal='WAIT',
                        setup=None, score=0, long_score=8, short_score=1,
                        regime='TREND_LONG', armed_side='LONG',
                        armed_trigger=102, armed_distance_atr=.05,
                        candle_time=123, volume_ratio=1.6, z_momentum=1.,
                        book_imbalance=.57, real_spread_pct=.0001,
                        expected_move_pct=.01, adx5=25, news={}, leader={})

    def test_armed_uses_directional_score(self):
        result = fly.armed_candidate(self.row)
        self.assertIsNotNone(result)
        self.assertEqual(result['score'], 8)
        self.assertEqual(self.row['score'], 0)
        with patch.object(base, 'last_entry_candle', {}):
            self.assertIs(fly.choose_best([self.row]), self.row)

    def test_armed_cost_news_and_health_gates(self):
        for changes in [dict(expected_move_pct=.001), dict(news={'bearish': True}),
                        dict(real_spread_pct=.002), dict(volume_ratio=.5)]:
            with self.subTest(changes=changes):
                self.assertIsNone(fly.armed_candidate(dict(self.row, **changes)))
        with patch.object(fly, '_setup_health', return_value={'enabled': False}):
            self.assertIsNone(fly.armed_candidate(self.row))

    def test_no_duplicate_candle(self):
        with patch.object(base, 'last_entry_candle', {'XRPUSDC':123}):
            self.assertIsNone(fly.choose_best([self.row]))

    def strategy(self, side='LONG', volume=1.2, reclaim=True, atr=.6, bearish=False, symbol='XRPUSDC'):
        # Prior 20-candle high/low remains unbroken, so only a pullback can qualify.
        rows = [[i,100,103,99,100,100] for i in range(60)]
        rows[-2] = [58,100,100.1 if reclaim else 100.7,99.8,100,100]
        rows[-1] = [59,100,100.7,99.9,100.6,volume*100]
        k5 = [[i,100,103,99,102,100] for i in range(60)]
        emas={9:100.2,21:100.,20:101.,50:100.}
        if side=='SHORT':
            rows=[[r[0],200-r[1],200-r[3],200-r[2],200-r[4],r[5]] for r in rows]
            k5=[[r[0],200-r[1],200-r[3],200-r[2],200-r[4],r[5]] for r in k5]
            emas={k:200-v for k,v in emas.items()}
        async def klines(symbol, interval, **kwargs):
            seq=rows if interval=='1m' else k5
            return seq+[seq[-1]]  # final candle is deliberately still open
        with patch.object(base,'get_klines',side_effect=klines), \
             patch.object(base,'ema',side_effect=lambda c,n:emas[n]), \
             patch.object(base,'rsi_wilder',return_value=55 if side=='LONG' else 45), \
             patch.object(base,'atr_wilder',return_value=atr), \
             patch.object(base,'adx_wilder',return_value=25), \
             patch.object(base,'macd_hist',return_value=(1,.5) if side=='LONG' else (-1,-.5)), \
             patch.object(base,'vwap',return_value=100), \
             patch.object(fly,'z_momentum',return_value=1 if side=='LONG' else -1), \
             patch.object(fly,'book',new=AsyncMock(return_value={'imbalance':.57 if side=='LONG' else .43,'spread_pct':.0001,'best_bid':100,'best_ask':100.01})), \
             patch.object(fly,'leader_context',new=AsyncMock(return_value={})), \
             patch.object(fly.news_signal,'get_news',new=AsyncMock(return_value={'bearish':bearish})):
            return asyncio.run(fly.strategy(symbol))

    def test_long_and_short_pullback_entries(self):
        for side in ('LONG','SHORT'):
            with self.subTest(side=side):
                a=self.strategy(side)
                self.assertEqual(a['signal'],side,a['reason'])
                self.assertEqual(a['setup'],'TREND_PULLBACK')
                self.assertGreaterEqual(a['ensemble_score'],fly.ENSEMBLE_MIN_SCORE)
                self.assertLess(a['price'],a['breakout_high'])
                self.assertGreater(a['price'],a['breakout_low'])

    def test_pullback_waits_for_confirmation_and_volume(self):
        for kwargs in [dict(reclaim=False),dict(volume=.6),dict(bearish=True),dict(atr=.2)]:
            with self.subTest(kwargs=kwargs):
                self.assertEqual(self.strategy(**kwargs)['signal'],'WAIT')

    def test_altcoin_news_reaches_strategy(self):
        for symbol in ('ETHUSDC', 'SOLUSDC'):
            a = self.strategy(symbol=symbol, bearish=True)
            self.assertTrue(a['news']['bearish'])
            self.assertEqual(a['signal'], 'WAIT')
            self.assertEqual(a['no_trade_reason'], 'NEGATIVE_NEWS_BLOCK')

if __name__=='__main__':
    unittest.main()
