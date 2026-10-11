"""Regression tests for news-only execution and persisted PAPER state transitions."""
import asyncio
import copy
import unittest
from unittest.mock import AsyncMock, patch
import news_paper as bot
import news_signal

NOW = 1800000065000
KEY_NEWS = dict(status='running', bullish=True, bearish=False,
                headlines=[dict(title='XRP ETF approved', score=5)])
CONFIG = dict(fee=.00095, slip=.0002, min_stop=.004, max_stop=.012, atr_mult=1.05)


def signal():
    return dict(signal='LONG', setup='NEWS_LONG', checked_ms=NOW,
                candle_time=NOW-65000, news_keys=bot.headline_keys(KEY_NEWS), atr=.008, price=1.4)


class PaperTests(unittest.TestCase):
    def step(self, state=None, price=1.4, a=None, news=None, now=NOW):
        return bot.advance(state or bot.initial(),dict(price=price,time=now),
                           a if a is not None else signal(),news or KEY_NEWS,now,CONFIG)

    def test_entry_risk_fees_and_target(self):
        s=self.step();p=s['position']
        self.assertIsNotNone(p)
        loss=-bot.net(p,p['stop_loss'])[0]
        self.assertLessEqual(loss,10000*bot.RISK+1e-8)
        self.assertAlmostEqual(bot.net(p,p['take_profit'])[0]/loss,bot.RR)
        self.assertLessEqual(p['entry_price']*p['qty'],3500+1e-8)

    def test_stale_negative_and_neutral_news_never_enter(self):
        for delta in [dict(status='stale'),dict(status='degraded'),dict(bearish=True),dict(bullish=False)]:
            self.assertIsNone(self.step(news=dict(KEY_NEWS,**delta))['position'])

    def test_only_news_long_with_fresh_matching_analysis(self):
        for delta in [dict(setup='BREAKOUT'),dict(signal='SHORT'),dict(checked_ms=NOW-30000),
                      dict(candle_time=NOW),dict(candle_time=NOW-200000),dict(news_keys=['other']),dict(atr=float('nan'))]:
            self.assertIsNone(self.step(a=dict(signal(),**delta))['position'])
        self.assertIsNone(self.step(price=1.5)['position'])

    def test_exit_works_during_feed_failure_and_dedup_survives_restart(self):
        s=self.step();p=s['position']
        s=self.step(s,price=p['take_profit']*1.001,news=dict(KEY_NEWS,status='stale'),now=NOW+1000)
        self.assertIsNone(s['position']);self.assertEqual(s['count'],1)
        # Serialize/restore precisely as PostgreSQL does.
        s=bot.json.loads(bot.json.dumps(s));later=NOW+2000000
        a=dict(signal(),checked_ms=later,candle_time=later-65000)
        s=self.step(s,a=a,now=later)
        self.assertIsNone(s['position']);self.assertIn('už jsem obchodoval',s['reason'])

    def test_daily_loss_and_invalid_quote(self):
        s=bot.initial();s.update(day=bot.iso(NOW)[:10],day_pnl=-80)
        self.assertIsNone(self.step(s)['position'])
        for q in [None,dict(price=1.4,time=NOW-20000),dict(price=float('nan'),time=NOW)]:
            self.assertIsNone(bot.advance(bot.initial(),q,signal(),KEY_NEWS,NOW,CONFIG)['position'])

    def test_same_candle_and_changed_news_do_not_duplicate(self):
        s=self.step();s.update(position=None)
        news=dict(KEY_NEWS,headlines=[dict(title='Ripple regulatory approval',score=4)])
        self.assertIsNone(self.step(s,a=dict(signal(),news_keys=bot.headline_keys(news)),news=news)['position'])


class BackgroundTests(unittest.IsolatedAsyncioTestCase):
    async def test_feed_updates_without_strategy_or_dashboard(self):
        seen=asyncio.Event()
        async def get(_):seen.set()
        with patch.object(news_signal,'get_news',side_effect=get) as refresh:
            task=asyncio.create_task(news_signal.background_loop())
            await asyncio.wait_for(seen.wait(),.5)
            task.cancel();await asyncio.gather(task,return_exceptions=True)
            refresh.assert_called_once_with('XRP')

    async def test_neutral_feed_skips_market_scan(self):
        with patch.object(news_signal,'cached_state',return_value=dict(KEY_NEWS,bullish=False)), \
             patch.object(bot.v8_fly_layer,'strategy',new_callable=AsyncMock) as strategy:
            await bot.scan_once(None)
            strategy.assert_not_called()

    async def test_independent_route_and_tasks_keep_fly_paused(self):
        import app_v8_fly as app
        self.assertIn('FLY',app.PAUSED_BOTS)
        self.assertFalse(app.portfolio_entry_allowed('FLY','XRPUSDC','LONG')[0])
        self.assertNotIn('NEWS_LONG',app.base.ENABLED_SETUPS)
        self.assertTrue(any(getattr(r,'path','')=='/news-paper/status' for r in app.app.routes))
        self.assertIn('newsPaper',__import__('news_dashboard').enhance('<div class="card muted" id="health"></div></body>'))

if __name__=='__main__':unittest.main()

class ConfirmationTests(unittest.IsolatedAsyncioTestCase):
    async def test_news_only_selects_news_and_never_plain_breakout(self):
        import app_v8 as base
        from contextlib import ExitStack
        fly=bot.v8_fly_layer
        rows=[[NOW-60000*(61-i),100,103,99,100,100] for i in range(60)]
        rows[-1]=[NOW-65000,100,103.2,100,103.1,200]
        async def klines(symbol,interval):return rows+[rows[-1]]
        def ema(c,n):return {9:100.2,21:100.,20:101.,50:100.}[n]
        with ExitStack() as stack:
            for name,value in [('get_klines',klines),('ema',ema)]:stack.enter_context(patch.object(base,name,side_effect=value))
            for name,value in [('rsi_wilder',55),('atr_wilder',1),('adx_wilder',25),('macd_hist',(1,.5)),('vwap',100)]:
                stack.enter_context(patch.object(base,name,return_value=value))
            stack.enter_context(patch.object(base,'trade_history',[]))
            stack.enter_context(patch.object(base,'ENABLED_SETUPS',{'BREAKOUT'}))
            stack.enter_context(patch.object(fly,'m',base))
            stack.enter_context(patch.object(fly,'z_momentum',return_value=1.5))
            stack.enter_context(patch.object(fly,'leader_context',new=AsyncMock(return_value={})))
            stack.enter_context(patch.object(fly,'book',new=AsyncMock(return_value=dict(imbalance=.6,spread_pct=.0001,best_bid=103.09,best_ask=103.1))))
            with patch.object(news_signal,'get_news',new=AsyncMock(return_value=KEY_NEWS)):
                a=await fly.strategy(bot.SYMBOL,news_only=True)
                self.assertEqual(a['signal'],'LONG',a['reason'])
                self.assertEqual(a['setup'],'NEWS_LONG')
                normal=await fly.strategy(bot.SYMBOL)
                self.assertEqual(normal['setup'],'BREAKOUT')
            with patch.object(news_signal,'get_news',new=AsyncMock(return_value=dict(KEY_NEWS,bullish=False))):
                a=await fly.strategy(bot.SYMBOL,news_only=True)
                self.assertEqual(a['signal'],'WAIT')
                self.assertIsNone(a['armed_side'])
