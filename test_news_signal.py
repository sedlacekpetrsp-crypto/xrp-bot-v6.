import asyncio
import time
import unittest
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime
from unittest.mock import patch
import httpx
import news_signal as news


def feed(title='XRP ETF approved', date=None):
    date = date or datetime.now(timezone.utc)
    return ('<rss><channel><item><title>'+title+'</title><link>https://coindesk.com/news/xrp</link><pubDate>'+format_datetime(date)+'</pubDate></item></channel></rss>').encode()


class NewsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        news._cache = {'ts': 0, 'data': news._neutral(), 'items': []}
        news._provider_state.clear()
        news._refresh_task = None

    async def test_valid_rss_and_score(self):
        items = news._parse_feed(feed(), 'coindesk.com')
        self.assertEqual(len(items), 1)
        self.assertTrue(news._summarize(items)['bullish'])

    async def test_old_future_missing_dates_and_unrelated_titles_rejected(self):
        for delta in [-121, 10]:
            self.assertEqual(news._parse_feed(feed(date=datetime.now(timezone.utc)+timedelta(minutes=delta)), 'coindesk.com'), [])
        self.assertEqual(news._parse_feed(feed('Cardano ETF approved'), 'coindesk.com'), [])
        self.assertEqual(news._parse_feed(feed().replace(b'pubDate', b'unknown'), 'coindesk.com'), [])

    async def test_predictions_negation_and_word_boundaries(self):
        for title in ['XRP ETF could be approved', 'XRP ETF not approved', 'XRP approval?', 'Ripple banking service']:
            self.assertEqual(news._headline_score(title)[0], 0)
        self.assertLess(news._headline_score('Ripple hacked')[0], 0)

    async def test_duplicate_titles_and_expiry(self):
        items = news._parse_feed(feed(), 'coindesk.com')
        self.assertEqual(news._summarize(items*2)['positive_count'], 1)
        items[0]['seen_at'] = (datetime.now(timezone.utc)-timedelta(hours=3)).isoformat()
        self.assertFalse(news._summarize(items)['bullish'])

    async def test_untrusted_link_and_entity_rejected(self):
        self.assertEqual(news._parse_feed(feed().replace(b'https://coindesk.com', b'https://bad.example'), 'coindesk.com'), [])
        with self.assertRaises(ValueError):
            news._parse_feed(b'<!DOCTYPE rss>'+feed(), 'coindesk.com')

    async def test_partial_failure_and_retry_after(self):
        def handler(request):
            if request.url.host == 'coindesk.com':
                return httpx.Response(200, content=feed())
            return httpx.Response(429, headers={'Retry-After': '3600'})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            good, bad = await asyncio.gather(news._fetch_source(client,'coindesk.com','https://coindesk.com/rss'), news._fetch_source(client,'decrypt.co','https://decrypt.co/feed'))
            self.assertTrue(good)
            self.assertEqual(bad, [])
            self.assertGreater(news._provider_state['decrypt.co']['retry_at']-time.monotonic(), 3590)
            self.assertEqual(await news._fetch_source(client,'decrypt.co','https://decrypt.co/feed'), [])

    async def test_refresh_partial_and_total_failure_clear_old_signals(self):
        def good(request):
            if request.url.host == 'www.coindesk.com':
                return httpx.Response(200, content=feed())
            return httpx.Response(503)
        original = httpx.AsyncClient
        with patch.object(news.httpx, 'AsyncClient', side_effect=lambda **kw: original(transport=httpx.MockTransport(good), **kw)):
            await news._refresh()
        self.assertEqual(news.cached_state()['active_sources'], 1)
        self.assertTrue(news.cached_state()['bullish'])
        def bad(request):
            return httpx.Response(503)
        with patch.object(news.httpx, 'AsyncClient', side_effect=lambda **kw: original(transport=httpx.MockTransport(bad), **kw)):
            await news._refresh()
        self.assertEqual(news.cached_state()['status'], 'degraded')
        self.assertFalse(news.cached_state()['bullish'])
        self.assertEqual(news.cached_state()['score'], 0)

    async def test_nonblocking_single_flight(self):
        started, release = asyncio.Event(), asyncio.Event()
        async def slow():
            started.set()
            await release.wait()
        with patch.object(news, '_refresh', side_effect=slow) as mocked:
            await asyncio.wait_for(news.get_xrp_news(), .1)
            await started.wait()
            await news.get_xrp_news()
            self.assertEqual(mocked.call_count, 1)
            release.set()
            await news._refresh_task

    async def test_cache_expires_and_is_not_mutable(self):
        news._cache.update(ts=time.monotonic()-400, items=news._parse_feed(feed(),'coindesk.com'))
        self.assertFalse(news.cached_state()['bullish'])
        self.assertEqual(news.cached_state()['status'], 'stale')
        news._cache['ts'] = time.monotonic()
        snapshot = news.cached_state()
        snapshot['headlines'].clear()
        self.assertTrue(news.cached_state()['headlines'])

class MultiAssetTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        news._cache = {"ts": time.monotonic(), "data": news._neutral(), "items": []}
        news._provider_state.clear()
        news._refresh_task = None

    async def test_aliases_and_isolation(self):
        for name, symbol in [("Bitcoin", "BTCUSDT"), ("Ethereum", "ETHUSDC"),
                             ("Solana", "SOLUSDC"), ("Ripple", "XRPUSDC")]:
            news._cache["items"] = news._parse_feed(feed(name + " ETF approved"), "coindesk.com")
            own = await news.get_news(symbol)
            self.assertTrue(own["bullish"])
            for asset in news.ASSETS:
                self.assertEqual(news.cached_state(asset)["bullish"], asset == own["asset"])
        for symbol in ["DOGE", "BTCFAKE", ""]:
            with self.assertRaises(ValueError):
                await news.get_news(symbol)

    async def test_mixed_headline_cannot_transfer_sentiment(self):
        news._cache["items"] = news._parse_feed(feed("Bitcoin ETF approved while Solana hacked"), "coindesk.com")
        for asset in ["BTC", "SOL"]:
            d = news.cached_state(asset)
            self.assertTrue(d["headlines"])
            self.assertEqual(d["score"], 0)
            self.assertFalse(d["bullish"] or d["bearish"])

    async def test_btc_filter_and_neutral_failure(self):
        import app_blue_whale_mirror as whale
        news._cache["items"] = news._parse_feed(feed("Bitcoin ETF approved"), "coindesk.com")
        with patch.object(whale, "WHALE_TECH_CONFIRM", False):
            ok, details = await whale.technical_confirmation(None, "SHORT")
            self.assertFalse(ok)
            self.assertEqual(details["reason"], "BTC_NEWS_CONFLICT")
            self.assertTrue((await whale.technical_confirmation(None, "LONG"))[0])
            news._cache["items"] = []
            self.assertTrue((await whale.technical_confirmation(None, "SHORT"))[0])
        news._cache["items"] = news._parse_feed(feed("Bitcoin hacked"), "coindesk.com")
        self.assertTrue(news.blocks_entry("BTCUSDT", "LONG"))
        self.assertFalse(news.blocks_entry("ETHUSDC", "LONG"))

    async def test_all_assets_share_single_refresh(self):
        release = asyncio.Event()
        async def slow():
            await release.wait()
        news._cache["ts"] = 0
        with patch.object(news, "_refresh", side_effect=slow) as mocked:
            await asyncio.gather(*(news.get_news(a) for a in news.ASSETS))
            await asyncio.sleep(0)
            self.assertEqual(mocked.call_count, 1)
            self.assertEqual(set(news.cached_all()["assets"]), set(news.ASSETS))
            release.set()
            await news._refresh_task


if __name__ == '__main__':
    unittest.main()
