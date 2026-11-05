import copy
import unittest
from datetime import timedelta
from unittest.mock import AsyncMock, patch
import app_blue_whale_mirror as w


def signal(i=1, side='LONG'):
    sl,tp=(79000,84000) if side=='LONG' else (81000,76000)
    return {'id':i,'text':f'BTC {side} ENTRY: 80000 SL: {sl} TP: {tp}',
            'entry':80000,'stop':w.parse_stop(f'SL: {sl}'),'tp':tp,
            'posted_at':w.utcnow().isoformat()}


class WhaleSignals(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.saved=copy.deepcopy(w.state)
        w.state.update(balance=10000,equity=10000,open_positions=[],open_position=None,
                       trades=[],seen_signal_ids=[],signal_checks=[],last_signal=None)
        self.saver=patch.object(w,'save_state'); self.saver.start()

    def tearDown(self):
        self.saver.stop();w.state.clear();w.state.update(self.saved)

    def test_recorded_adverts_cannot_open(self):
        for raw in ['819xx','82xxx']:
            text=f'$BTC SL: {raw} Only use 2% of your capital! DM @Oldman899 to join VIP now'
            self.assertIsNone(w.parse_stop(text))
            self.assertIsNone(w.infer_side(text,{'low':82000,'high':82999},80000))
            s={'id':4153,'text':text,'stop':w.parse_stop(text)}
            self.assertFalse(w.open_paper(s,'SHORT',80000))
        self.assertEqual(w.state['balance'],10000)
        self.assertEqual(w.state['open_positions'],[])

    def test_exact_stop_numbers(self):
        for text in ['SL: 81900','SL: 81,900','SL: 81900.50']:
            self.assertAlmostEqual(w.parse_stop(text)['low'],81900.5 if '.50' in text else 81900)
        for text in ['SL: 819xx','SL: 82xxx','SL: 81900XYZ','SL: 81,90','SL: 81900.5.2']:
            self.assertIsNone(w.parse_stop(text),text)

    def test_long_and_short_use_source_tp(self):
        for side in ['LONG','SHORT']:
            w.state['open_positions']=[]
            self.assertTrue(w.open_paper(signal(side=side),side,80000))
            self.assertEqual(w.state['open_positions'][0]['tp'],signal(side=side)['tp'])
            self.assertGreater(w.state['open_positions'][0]['entry_fee'],0)

    def test_invalid_or_unprofitable_levels_rejected(self):
        s=signal();s['tp']=80050
        self.assertFalse(w.open_paper(s,'LONG',80000))
        s=signal();s['tp']=78000
        self.assertFalse(w.open_paper(s,'LONG',80000))
        self.assertEqual(w.state['balance'],10000)

    # The scanner no longer consumes Telegram posts (latest_signals is not called by
    # scan_entries). The three obsolete Telegram-flow tests are replaced by the same
    # properties on the current candle scanner: retry, isolation and no consumption.
    def scanner(self, confirm, symbols=('BTCUSDT',), broken=()):
        class Response:
            def __init__(self, params): self.params=params or {}
            def json(self):
                return 'BROKEN' if self.params.get('symbol') in broken and 'interval' in self.params else {'price':'100'}
        async def get(client,url,params=None,timeout=None): return Response(params)
        def closed(raw,now,minutes):
            if raw=='BROKEN': raise ValueError('stale candles')
            return []
        cand=lambda _: (dict(side='LONG',entry=100,stop=99,tp=104,key='swing-1',strategy='FIB_618_786',confirmation={}),
                        {'strategy':'FIB_618_786','reason':'ready'})
        return [patch.object(w,'SYMBOLS',symbols),patch.object(w,'market_get',new=get),
                patch.object(w,'closed_candles',side_effect=closed),patch.object(w,'fib_candidate',side_effect=cand),
                patch.object(w,'vwap_candidate',return_value=(None,{'strategy':'VWAP_REVERSION','reason':'waiting'})),
                patch.object(w,'technical_confirmation',new=confirm),
                patch.object(w,'scan_trendline',new=AsyncMock(return_value={'symbol':'XRPUSDT','strategy':'TRENDLINE_4H_LONG','reason':'mock'}))]

    async def run_scan(self, patches):
        for p in patches: p.start()
        try: await w.scan_entries(None)
        finally:
            for p in reversed(patches): p.stop()

    async def test_transient_mtf_rejection_retries_then_no_duplicate(self):
        w.state.update(persistence='postgres',persistence_error=None)
        confirm=AsyncMock(side_effect=[(False,{'score':1,'min_score':3}),(True,{'score':3})])
        patches=self.scanner(confirm)
        await self.run_scan(patches)
        self.assertEqual(w.state['open_positions'],[]); self.assertEqual(w.state['seen_signal_ids'],[])
        await self.run_scan(patches)
        self.assertEqual(len(w.state['open_positions']),1); self.assertEqual(len(w.state['seen_signal_ids']),1)
        await self.run_scan(patches)
        self.assertEqual(len(w.state['open_positions']),1)
        self.assertEqual(confirm.await_count,2)

    async def test_broken_market_does_not_hide_valid_setup_elsewhere(self):
        w.state.update(persistence='postgres',persistence_error=None)
        await self.run_scan(self.scanner(AsyncMock(return_value=(True,{'score':3})),
                                         symbols=('BTCUSDT','ETHUSDT'),broken=('BTCUSDT',)))
        self.assertEqual([p['symbol'] for p in w.state['open_positions']],['ETHUSDT'])
        errors=[d for d in w.state['signal_checks'] if d.get('error')]
        self.assertEqual([d['symbol'] for d in errors],['BTCUSDT'])

    async def test_unconfirmed_wait_does_not_consume_setup(self):
        w.state.update(persistence='postgres',persistence_error=None)
        await self.run_scan(self.scanner(AsyncMock(return_value=(False,{'score':2,'min_score':3}))))
        self.assertEqual(w.state['open_positions'],[]); self.assertEqual(w.state['seen_signal_ids'],[])
        self.assertIn('MTF',w.state['signal_checks'][0]['reason'])
        await self.run_scan(self.scanner(AsyncMock(return_value=(True,{'score':3}))))
        self.assertEqual(len(w.state['open_positions']),1)

    async def test_expired_and_future_signals_never_open(self):
        for minutes in [-20,5]:
            s=signal();s['posted_at']=(w.utcnow()+timedelta(minutes=minutes)).isoformat()
            with patch.object(w,'latest_signals',AsyncMock(return_value=[s])),patch.object(w,'technical_confirmation',AsyncMock()) as confirm:
                await w.scan_entries(None,80000)
                confirm.assert_not_awaited()
            self.assertFalse(w.state['open_positions'])

    async def test_source_returns_all_candidates(self):
        s=signal();text=''.join(f'<div class="tgme_widget_message_wrap"><div data-post="BlueWhaleCryptoTrading/{i}"><div class="tgme_widget_message_text">{s["text"]}</div><time datetime="{s["posted_at"]}"></time></div></div>' for i in [10,11])
        class Response:
            def raise_for_status(self):pass
        r=Response();r.text=text
        client=AsyncMock();client.get.return_value=r
        found=await w.latest_signals(client)
        self.assertEqual([s['id'] for s in found],[10,11])
        self.assertEqual(found[0]['entry'],80000)
        self.assertEqual(found[0]['tp'],84000)

if __name__=='__main__':unittest.main()
