"""Fetch official option trades and run the frozen weekly skew screen."""
import concurrent.futures,datetime as dt,gzip,hashlib,json,pathlib,sys,time,urllib.parse,urllib.request
from dataclasses import replace
from research.btc_option_skew_risk_on_v1 import Config,DAY,backtest,skew_observation,validate_prices
UTC=dt.timezone.utc;DERIBIT='https://history.deribit.com/api/v2/public/get_last_trades_by_currency_and_time';BINANCE='https://data-api.binance.vision/api/v3/klines'
def stamp(y,m=1,d=1):return int(dt.datetime(y,m,d,tzinfo=UTC).timestamp()*1000)
def get(url,path,retries=6):
    if path.exists():return path.read_bytes()
    for k in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'xrp-research/1.0'}),timeout=180) as r:raw=r.read()
            path.write_bytes(raw);return raw
        except Exception:
            if k+1==retries:raise
            time.sleep(min(2**k,20))
def interval(friday,a,b,cache,depth=0):
    q=urllib.parse.urlencode(dict(currency='BTC',kind='option',start_timestamp=a,end_timestamp=b,count=1000,sorting='asc',include_old='true'));url=DERIBIT+'?'+q;name=f"deribit-{dt.datetime.fromtimestamp(friday/1000,UTC):%Y%m%d}-{a}-{b}.json";raw=get(url,cache/name);doc=json.loads(raw)
    if 'error' in doc:raise ValueError(doc['error'])
    trades=doc['result']['trades'];more=bool(doc['result']['has_more']);item=dict(kind='deribit_BTC_option_trades',week=friday,url=url,cache_file=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),rows=len(trades),has_more=more,used=not more)
    if not more:return trades,[item]
    if b<=a or depth>=20:raise ValueError('cannot complete Deribit interval')
    mid=(a+b)//2;left,lm=interval(friday,a,mid,cache,depth+1);right,rm=interval(friday,mid+1,b,cache,depth+1);item['used']=False
    return left+right,[item]+lm+rm
def week(friday,cache):
    trades,manifest=interval(friday,friday+12*3_600_000,friday+13*3_600_000-1,cache);unique={str(x['trade_id']):x for x in trades};return skew_observation(list(unique.values()),friday),manifest
def prices(cache):
    start=stamp(2020);end=stamp(2026,10)-1;cursor=start;page=0;rows=[];manifest=[]
    while cursor<=end:
        q=urllib.parse.urlencode(dict(symbol='XRPUSDT',interval='1d',startTime=cursor,endTime=end,limit=1000));url=BINANCE+'?'+q;name=f'XRPUSDT-1d-api-{page}.json';raw=get(url,cache/name);doc=json.loads(raw);manifest.append(dict(kind='binance_XRPUSDT_1d',url=url,cache_file=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),rows=len(doc),used=True))
        if not doc:break
        rows += [dict(timestamp=int(x[0]),open=float(x[1]),high=float(x[2]),low=float(x[3]),close=float(x[4])) for x in doc];cursor=int(doc[-1][0])+DAY;page+=1
        if len(doc)<1000:break
    return rows,manifest
def metrics(t,curve,initial=10000.):
    w=sum(max(0,x['pnl']) for x in t);l=-sum(min(0,x['pnl']) for x in t);n=sum(x['pnl'] for x in t);peak=initial;dd=0
    for x in curve:peak=max(peak,x['equity']);dd=max(dd,(peak-x['equity'])/peak*100)
    return dict(trades=len(t),net_pnl=n,net_return_pct=n/initial*100,profit_factor=w/l if l else None,expectancy=n/len(t) if t else None,max_drawdown_pct=dd,fees=sum(x['fees'] for x in t),slippage_cost=sum(x['slippage_cost'] for x in t),gross_profit=w,gross_loss=l)
def main():
    cache=pathlib.Path(sys.argv[1]);dest=pathlib.Path(sys.argv[2]);cache.mkdir(parents=True,exist_ok=True);dest.mkdir(parents=True,exist_ok=True)
    fridays=[];d=dt.date(2021,1,1)
    while d<=dt.date(2026,9,25):
        if d.weekday()==4:fridays.append(int(dt.datetime.combine(d,dt.time(),UTC).timestamp()*1000))
        d+=dt.timedelta(days=1)
    observations=[];manifest=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures={pool.submit(week,f,cache):f for f in fridays}
        for n,fut in enumerate(concurrent.futures.as_completed(futures),1):
            o,m=fut.result();observations.append(o);manifest+=m
            if n%25==0:print('option weeks',n,'of',len(fridays),flush=True)
    observations.sort(key=lambda x:x['friday_timestamp']);manifest.sort(key=lambda x:(x.get('week',0),x['url']));rows,pm=prices(cache);manifest+=pm;validate_prices(rows);signals={x['entry_timestamp']:x for x in observations if x.get('eligible') and x.get('signal')}
    for x in rows:
        if x['timestamp'] in signals:x['skew_signal']=signals[x['timestamp']]
    folds=[('2021_control',stamp(2021),stamp(2022))]+[(str(y),stamp(y),stamp(y+1) if y<2026 else stamp(2026,10)) for y in range(2022,2027)]+[('continuous_oos',stamp(2022),stamp(2026,10))];runs={};ledgers={}
    for name,start,end in folds:
        for label,mul in (('base',1),('stress',2)):
            c=replace(Config(),fee=Config().fee*mul,slippage=Config().slippage*mul);t,curve=backtest(rows,start,end,c);key=name+'_'+label;ledgers[key]=t;runs[key]=metrics(t,curve);print(key,runs[key],flush=True)
    years=[str(x) for x in range(2022,2027)];base=[x for y in years for x in ledgers[y+'_base']];stress=[x for y in years for x in ledgers[y+'_stress']];agg=metrics(base,[]);aggs=metrics(stress,[]);agg['max_drawdown_pct']=None;aggs['max_drawdown_pct']=None
    by={y:runs[y+'_base']['net_pnl'] for y in years};bys={y:runs[y+'_stress']['net_pnl'] for y in years};positive=sum(max(0,v) for v in by.values());share=max((max(0,v)/positive for v in by.values()),default=1)
    gates=dict(sample=agg['trades']>=100,base_net=agg['net_pnl']>0,base_expectancy=(agg['expectancy'] or 0)>0,base_pf=(agg['profit_factor'] or 0)>1.20,stress_net=aggs['net_pnl']>0,stress_expectancy=(aggs['expectancy'] or 0)>0,stress_pf=(aggs['profit_factor'] or 0)>1.05,four_years=sum(v>0 for v in by.values())>=4,four_years_stress=sum(v>0 for v in bys.values())>=4,final_year=by['2026']>0 and bys['2026']>0,drawdown=max(runs['continuous_oos_base']['max_drawdown_pct'],runs['continuous_oos_stress']['max_drawdown_pct'])<=10,concentration=agg['net_pnl']>0 and positive>0 and share<=.50,audit=False,forward_paper=False)
    historical=all(v for k,v in gates.items() if k not in ('audit','forward_paper'));proto=pathlib.Path('research/btc_option_skew_risk_on_protocol_20261030.md');coverage=dict(total_weeks=len(observations),eligible_weeks=sum(x['eligible'] for x in observations),positive_skew_weeks=sum(bool(x.get('signal')) for x in observations),by_year={str(y):dict(total=sum(dt.datetime.fromtimestamp(x['friday_timestamp']/1000,UTC).year==y for x in observations),eligible=sum(x['eligible'] and dt.datetime.fromtimestamp(x['friday_timestamp']/1000,UTC).year==y for x in observations),positive=sum(bool(x.get('signal')) and dt.datetime.fromtimestamp(x['friday_timestamp']/1000,UTC).year==y for x in observations)) for y in range(2021,2027)})
    result=dict(strategy='BTC_OPTION_SKEW_RISK_ON_XRP_V1',status='TEST NEDOKONCEN: independent audit and forward PAPER required' if historical else 'NEPROSEL',protocol_sha256=hashlib.sha256(proto.read_bytes()).hexdigest(),manifest=manifest,coverage=coverage,data_quality=dict(price_rows=len(rows),price_start=rows[0]['timestamp'],price_end=rows[-1]['timestamp'],price_gaps=[]),runs=runs,aggregate_oos=agg,aggregate_stress=aggs,by_year=by,stress_by_year=bys,positive_year_profit_concentration=share,gates=gates,historical_pass_before_audit=historical,limitations=['Trade-print skew is not a synchronized or executable quote surface.','Zero-rate Black-Scholes delta is a fixed approximation.','Missing or thin option sides create no signal and are not imputed.','Daily XRP OHLC cannot reconstruct tick paths; conservative stop/gap rules apply.','Local SHA256 values are not publisher signatures.','No independent forward PAPER evidence exists.'])
    (dest/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');
    with gzip.open(dest/'observations.json.gz','wt') as h:json.dump(observations,h)
    with gzip.open(dest/'trades.json.gz','wt') as h:json.dump(ledgers,h)
    print(result['status'],gates,coverage,flush=True)
if __name__=='__main__':main()
