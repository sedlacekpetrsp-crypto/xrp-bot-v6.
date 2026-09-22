import asyncio,sys,time,math
from email.utils import formatdate
import httpx,pytest
from market_data import MarketData,MarketDataUnavailable,retry_seconds
BASE='https://data-api.binance.vision/api/v3/'
def response(code=200, data=None, headers=None):
 return httpx.Response(code,json=data or {},headers=headers,request=httpx.Request('GET',BASE))
def candles(interval=1):
 now=int(time.time()//(interval*60))*(interval*60000)
 return [[now-interval*60000,1,2,.5,1.2,10,now-1],[now,1.2,2,.5,1.3,8,now+interval*60000-1]]
class Client:
 def __init__(self,handler):self.handler=handler;self.calls=[]
 async def get(self,url,params=None,timeout=None):
  self.calls.append((url,params));await asyncio.sleep(0)
  return self.handler(url,params)
@pytest.mark.asyncio
async def test_concurrent_cache_deduplicates():
 m=MarketData();c=Client(lambda u,p:response(data=candles()))
 rs=await asyncio.gather(*(m.get(c,BASE+'klines',{'symbol':'XRPUSDT','interval':'1m','limit':2}) for _ in range(12)))
 assert len(c.calls)==1
 rs[0].json()[0][1]=999
 assert rs[1].json()[0][1]==1
@pytest.mark.asyncio
async def test_ban_stops_entire_host_and_transitions():
 m=MarketData();c=Client(lambda u,p:response(418,{'msg':'banned'}, {'Retry-After':'172800'}))
 results=await asyncio.gather(*(m.get(c,BASE+'ticker/price',{'symbol':s}) for s in ['XRPUSDT','ETHUSDT','SOLUSDT']),return_exceptions=True)
 assert all(isinstance(x,MarketDataUnavailable) for x in results)
 assert len(c.calls)==1 and m.blocked['binance']>time.time()+172790
 assert m.provider=='kraken'
 # Retry during transition doesn't make requests to either exchange.
 with pytest.raises(MarketDataUnavailable):await m.get(c,BASE+'ticker/price',{'symbol':'BTCUSDT'})
 assert len(c.calls)==1
@pytest.mark.asyncio
async def test_fallback_quote_and_ohlc_conversion():
 m=MarketData();m.provider='kraken'
 raw=[[int(x[0]/1000),*x[1:5], '1.0',x[5],12] for x in candles(5)]
 c=Client(lambda u,p:response(data={'error':[],'result':{'XRPUSDC':raw,'last':1}}))
 r=await m.get(c,BASE+'klines',{'symbol':'XRPUSDC','interval':'5m','limit':2})
 assert c.calls[0][1]['pair']=='XRPUSDC'
 assert r.json()[0][5]=='10' and r.json()[0][8]==12
 assert r.json()[0][6]-r.json()[0][0]==299999
@pytest.mark.asyncio
async def test_depth_never_replays_snapshot():
 m=MarketData();m.provider='kraken'
 c=Client(lambda u,p:response(data={'error':[],'result':{'XRPUSDC':{'bids':[['1','2',100]],'asks':[['2','3',100]]}}}))
 for _ in range(2):
  m.next_request['kraken']=0
  r=await m.get(c,BASE+'depth',{'symbol':'XRPUSDC','limit':20})
  assert r.json()['bids']==[['1','2']]
 assert len(c.calls)==2
@pytest.mark.asyncio
async def test_invalid_price_never_becomes_zero_or_cache():
 m=MarketData();c=Client(lambda u,p:response(data={'price':'0'}))
 with pytest.raises(MarketDataUnavailable):await m.get(c,BASE+'ticker/price',{'symbol':'XRPUSDT'})
 assert not m.cache
@pytest.mark.asyncio
async def test_stale_candles_rejected():
 m=MarketData();rows=candles()
 # Shift both timestamps: stale candles must not retain a current close time.
 for row in rows: row[0]-=3600000;row[6]-=3600000
 c=Client(lambda u,p:response(data=rows))
 with pytest.raises(MarketDataUnavailable):await m.get(c,BASE+'klines',{'symbol':'XRPUSDT','interval':'1m'})
 assert not m.cache
@pytest.mark.asyncio
async def test_unknown_kraken_pair_never_substitutes_quote():
 m=MarketData();m.provider='kraken';c=Client(lambda u,p:response(data={'error':['EQuery:Unknown asset pair']}))
 with pytest.raises(MarketDataUnavailable):await m.get(c,BASE+'ticker/price',{'symbol':'FETUSDC'})
 assert c.calls[0][1]['pair']=='FETUSDC' and len(c.calls)==1
@pytest.mark.asyncio
async def test_kraken_rate_limit_pauses_all_pairs():
 m=MarketData();m.provider='kraken';c=Client(lambda u,p:response(data={'error':['EAPI:Rate limit exceeded']}))
 for s in ['XRPUSDT','ETHUSDT']:
  with pytest.raises(MarketDataUnavailable):await m.get(c,BASE+'ticker/price',{'symbol':s})
 assert len(c.calls)==1
@pytest.mark.asyncio
async def test_expired_cache_not_used_on_outage():
 m=MarketData();c=Client(lambda u,p:response(data={'price':'1.3'}))
 await m.get(c,BASE+'ticker/price',{'symbol':'XRPUSDT'})
 key=next(iter(m.cache));m.cache[key]=(0,*m.cache[key][1:])
 c.handler=lambda u,p:response(418)
 with pytest.raises(MarketDataUnavailable):await m.get(c,BASE+'ticker/price',{'symbol':'XRPUSDT'})
 assert not m.cache
@pytest.mark.asyncio
async def test_non_market_endpoint_denied():
 m=MarketData();c=Client(lambda u,p:response())
 with pytest.raises(MarketDataUnavailable):await m.get(c,BASE+'account')
 assert not c.calls

def test_retry_formats():
 assert retry_seconds(response(headers={'Retry-After':'172800'}),60)==172800
 assert retry_seconds(response(headers={'Retry-After':formatdate(time.time()+7200,usegmt=True)}),60)>7190
 assert retry_seconds(response(data={'retryAfter':int((time.time()+8000)*1000)}),60)>7990
 assert retry_seconds(response(data={'msg':f'IP banned until {int((time.time()+9000)*1000)}'}),60)>8990

@pytest.mark.asyncio
async def test_configured_gateway_preserves_origin_prefix_and_params():
 m=MarketData();c=Client(lambda u,p:response(data={'price':'1.3'}))
 url='https://configured-gateway.example/binance/api/v3/ticker/price'
 r=await m.get(c,url,{'symbol':'XRPUSDC'})
 assert c.calls[0]==(url,{'symbol':'XRPUSDC'})
 assert r.json()['price']=='1.3'
