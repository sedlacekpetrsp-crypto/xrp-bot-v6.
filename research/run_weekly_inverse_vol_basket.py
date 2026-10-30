"""Download frozen daily basket data and run annual/continuous validation."""
import datetime as dt,gzip,hashlib,json,math,pathlib,sys,urllib.parse,urllib.request
from dataclasses import replace
from research.weekly_inverse_vol_basket_v1 import Config,DAY,backtest,validate_markets

UTC=dt.timezone.utc;SYMBOLS=('XRPUSDT','BTCUSDT','ETHUSDT');API='https://data-api.binance.vision/api/v3/klines'
def stamp(y,m=1,d=1):return int(dt.datetime(y,m,d,tzinfo=UTC).timestamp()*1000)
START=stamp(2020);END=stamp(2026,10)-1

def get(url,path):
    if not path.exists():
        req=urllib.request.Request(url,headers={'User-Agent':'xrp-research/1.0'})
        with urllib.request.urlopen(req,timeout=120) as r:path.write_bytes(r.read())
    return path.read_bytes()

def download(symbol,cache):
    rows=[];manifest=[];cursor=START;page=0
    while cursor<=END:
        q=urllib.parse.urlencode(dict(symbol=symbol,interval='1d',startTime=cursor,endTime=END,limit=1000));url=API+'?'+q;path=cache/f'{symbol}-1d-api-{page}.json';raw=get(url,path);doc=json.loads(raw)
        if not isinstance(doc,list):raise ValueError(symbol+' invalid API response')
        manifest.append(dict(symbol=symbol,url=url,cache_file=path.name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),rows=len(doc)))
        if not doc:break
        for x in doc:
            t=int(x[0]);rows.append(dict(timestamp=t,open=float(x[1]),high=float(x[2]),low=float(x[3]),close=float(x[4])))
        nxt=int(doc[-1][0])+DAY
        if nxt<=cursor:raise ValueError('pagination did not advance')
        cursor=nxt;page+=1
        if len(doc)<1000:break
    return rows,manifest

def metrics(trades,curve,initial=10_000.0):
    win=sum(max(0,x['pnl']) for x in trades);loss=-sum(min(0,x['pnl']) for x in trades);net=sum(x['pnl'] for x in trades);peak=initial;dd=0
    for x in curve:
        peak=max(peak,x['equity']);dd=max(dd,(peak-x['conservative_equity'])/peak*100)
    return dict(trades=len(trades),net_pnl=net,net_return_pct=net/initial*100,profit_factor=win/loss if loss else None,expectancy=net/len(trades) if trades else None,max_drawdown_pct=dd,fees=sum(x['fees'] for x in trades),slippage_cost=sum(x['slippage_cost'] for x in trades),gross_profit=win,gross_loss=loss)

def main():
    cache=pathlib.Path(sys.argv[1]);dest=pathlib.Path(sys.argv[2]);cache.mkdir(parents=True,exist_ok=True);dest.mkdir(parents=True,exist_ok=True)
    markets={};manifest=[]
    for s in SYMBOLS:
        markets[s],m=download(s,cache);manifest+=m
    validate_markets(markets)
    folds=[('2021_control',stamp(2021),stamp(2022))]+[(str(y),stamp(y),stamp(y+1) if y<2026 else stamp(2026,10)) for y in range(2022,2027)]+[('continuous_oos',stamp(2022),stamp(2026,10))]
    runs={};ledgers={};curves={}
    for name,start,end in folds:
        for label,mul in (('base',1),('stress',2)):
            c=replace(Config(),fee=Config().fee*mul,slippage=Config().slippage*mul);t,curve,_=backtest(markets,start,end,c);key=name+'_'+label;ledgers[key]=t;curves[key]=curve;runs[key]=metrics(t,curve);print(key,runs[key],flush=True)
    years=[str(y) for y in range(2022,2027)];base=[x for y in years for x in ledgers[y+'_base']];stress=[x for y in years for x in ledgers[y+'_stress']]
    aggregate=metrics(base,[]);aggregate_stress=metrics(stress,[]);aggregate['max_drawdown_pct']=None;aggregate_stress['max_drawdown_pct']=None
    by_year={y:runs[y+'_base']['net_pnl'] for y in years};stress_year={y:runs[y+'_stress']['net_pnl'] for y in years}
    by_asset={s:sum(x['pnl'] for x in base if x['symbol']==s) for s in SYMBOLS};stress_asset={s:sum(x['pnl'] for x in stress if x['symbol']==s) for s in SYMBOLS}
    positive=sum(max(0,v) for v in by_year.values());max_share=max((max(0,v)/positive for v in by_year.values()),default=1)
    gates=dict(sample=aggregate['trades']>=600,base_net=aggregate['net_pnl']>0,base_expectancy=(aggregate['expectancy'] or 0)>0,base_pf=(aggregate['profit_factor'] or 0)>1.15,stress_net=aggregate_stress['net_pnl']>0,stress_expectancy=(aggregate_stress['expectancy'] or 0)>0,stress_pf=(aggregate_stress['profit_factor'] or 0)>1.05,every_asset=all(v>0 for v in by_asset.values()),every_asset_stress=all(v>0 for v in stress_asset.values()),four_years=sum(v>0 for v in by_year.values())>=4,four_years_stress=sum(v>0 for v in stress_year.values())>=4,final_year=by_year['2026']>0 and stress_year['2026']>0,drawdown=max(runs['continuous_oos_base']['max_drawdown_pct'],runs['continuous_oos_stress']['max_drawdown_pct'])<=25,concentration=aggregate['net_pnl']>0 and positive>0 and max_share<=.50,audit=False,forward_paper=False)
    historical=all(v for k,v in gates.items() if k not in ('audit','forward_paper'));proto=pathlib.Path('research/weekly_inverse_vol_basket_protocol_20261030.md')
    result=dict(strategy='CRYPTO_WEEKLY_INVERSE_VOL_BASKET_V1',status='TEST NEDOKONCEN: independent audit and forward PAPER required' if historical else 'NEPROSEL',protocol_sha256=hashlib.sha256(proto.read_bytes()).hexdigest(),manifest=manifest,data_quality=dict(symbols=list(SYMBOLS),rows={s:len(x) for s,x in markets.items()},start={s:x[0]['timestamp'] for s,x in markets.items()},end={s:x[-1]['timestamp'] for s,x in markets.items()},exact_alignment=True,gaps=[]),runs=runs,aggregate_oos=aggregate,aggregate_stress=aggregate_stress,by_year=by_year,stress_by_year=stress_year,by_asset=by_asset,stress_by_asset=stress_asset,positive_year_profit_concentration=max_share,gates=gates,historical_pass_before_audit=historical,limitations=['Long-only results include broad crypto beta and are not proof of alpha.','Weekly full liquidation and repurchase is conservative but actual liquidity, latency and taxes can differ.','Daily OHLC cannot reconstruct intraday paths; stop-first and adverse gap rules are fixed approximations.','Local SHA256 values are not publisher signatures.','No independent forward PAPER evidence exists.'])
    (dest/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    with gzip.open(dest/'trades.json.gz','wt') as h:json.dump(ledgers,h)
    print(result['status'],gates,flush=True)

if __name__=='__main__':main()
