import asyncio
import copy
import time
import unittest
from contextlib import ExitStack
from unittest.mock import AsyncMock, patch
import app_blue_whale_mirror as w


class FreshnessTests(unittest.TestCase):
    def setUp(self):
        self.saved=copy.deepcopy(w.state)
        w.state.update(balance=10000,equity=10000,open_positions=[],trades=[],seen_signal_ids=[],market_prices={},persistence='postgres',persistence_error=None)
    def tearDown(self):
        w.state.clear();w.state.update(self.saved)
    def signal(self):
        return dict(id=1,text='LONG',symbol='BTCUSDT',entry=100,tp=104,stop=dict(low=99,high=99,raw='99',masked=False))
    def test_invalid_prices_never_mutate_account(self):
        for value in (float('nan'),float('inf'),0,-1):
            with self.subTest(value=value):
                self.assertFalse(w.open_paper(self.signal(),'LONG',value))
                self.assertEqual(w.state['balance'],10000)
                self.assertEqual(w.state['open_positions'],[])
        s=self.signal();s['tp']=float('nan')
        self.assertFalse(w.open_paper(s,'LONG',100))
    def rows(self,minutes,stale=False):
        step=minutes*60000;end=int(time.time()*1000)//step*step
        if stale:end-=step*3
        return [[end+(i-70)*step,100,101,99,100,10,end+(i-69)*step-1] for i in range(70)]
    def confirm(self,rows):
        response=type('Response',(),{'json':lambda _:rows})()
        with patch.object(w.news_signal,'get_news',AsyncMock(return_value={})),patch.object(w.news_signal,'blocks_entry',return_value=False),patch.object(w,'WHALE_TECH_CONFIRM',True),patch.object(w,'market_get',AsyncMock(return_value=response)):
            return asyncio.run(w.technical_confirmation(None,'BTCUSDT','LONG'))
    def test_stale_confirmation_rejected(self):
        with self.assertRaises(ValueError):self.confirm(self.rows(5,True))
    def test_gap_in_confirmation_rejected(self):
        rows=self.rows(5);del rows[-10]
        with self.assertRaises(ValueError):self.confirm(rows)
    def test_closed_only_response_keeps_latest_bar(self):
        async def get(client,url,**kwargs):
            minutes={'5m':5,'15m':15,'1h':60}[kwargs['params']['interval']]
            rows=self.rows(minutes);rows[-1][4]=100.5
            return type('Response',(),{'json':lambda _:rows})()
        with patch.object(w.news_signal,'get_news',AsyncMock(return_value={})),patch.object(w.news_signal,'blocks_entry',return_value=False),patch.object(w,'WHALE_TECH_CONFIRM',True),patch.object(w,'market_get',side_effect=get):
            _,details=asyncio.run(w.technical_confirmation(None,'BTCUSDT','LONG'))
        for frame in ('5m','15m','1h'):
            self.assertEqual(details['details'][frame]['close'],100.5)
    def test_execution_uses_post_confirmation_price(self):
        class Response:
            def __init__(self,price):self.price=price
            def json(self):return {'price':str(self.price)}
        prices=iter([100,102])
        async def get(client,url,**kwargs):
            return Response(next(prices)) if url==w.BINANCE_PRICE_URL else Response(0)
        candidate=dict(side='LONG',entry=100,stop=99,tp=104,key='swing',strategy='FIB_618_786')
        with ExitStack() as stack:
            for name,value in [('SYMBOLS',('BTCUSDT',)),('closed_candles',lambda *args:[]),('fib_candidate',lambda _: (copy.deepcopy(candidate),{'strategy':'FIB_618_786','reason':'ready'})),('vwap_candidate',lambda *args:(None,{'strategy':'VWAP_REVERSION','reason':'wait'}))]:stack.enter_context(patch.object(w,name,value))
            stack.enter_context(patch.object(w,'market_get',side_effect=get))
            stack.enter_context(patch.object(w,'technical_confirmation',AsyncMock(return_value=(True,{}))))
            stack.enter_context(patch.object(w,'scan_trendline',AsyncMock(return_value={'symbol':'XRPUSDT','strategy':'TRENDLINE','reason':'wait'})))
            asyncio.run(w.scan_entries(None))
        self.assertEqual(w.state['market_prices']['BTCUSDT'],102)
        self.assertEqual(w.state['open_positions'],[])
        self.assertIn('blízkosti',w.state['last_signal']['rejected'])

if __name__=='__main__':unittest.main()
