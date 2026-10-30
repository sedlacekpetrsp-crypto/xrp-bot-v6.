import datetime as dt,gzip,hashlib,json,pathlib,sys,urllib.parse,urllib.request
from dataclasses import replace
from research.btc_hashrate_shock_recovery_v1 import Config,DAY,backtest,make_signals,validate
UTC=dt.timezone.utc;CM='https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=btc&metrics=HashRate&frequency=1d&page_size=10000';BI='https://data-api.binance.vision/api/v3/klines'
def stamp(y,m=1):return int(dt.datetime(y,m,1,tzinfo=UTC).timestamp()*1000)
def get(url,p):
    if not p.exists():
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'xrp-research/1.0'}),timeout=180) as r:p.write_bytes(r.read())
    return p.read_bytes()
def load_metric(cache):
    p=cache/'coinmetrics-btc-hashrate.json';raw=get(CM,p);doc=json.loads(raw);rows=[]
    for x in doc['data']:
        t=int(dt.datetime.fromisoformat(x['time'].replace('Z','+00:00')).timestamp()*1000);v=float(x['HashRate'])
        if v<=0:raise ValueError('nonpositive hashrate')
        rows.append(dict(timestamp=t,hashrate=v))
    return rows,dict(kind='coinmetrics_BTC_HashRate',url=CM,cache_file=p.name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),rows=len(rows))
def load_prices(cache):
    start=stamp(2020);end=stamp(2026,10)-1;cursor=start;page=0;rows=[];man=[]
    while cursor<=end:
        q=urllib.parse.urlencode(dict(symbol='XRPUSDT',interval='1d',startTime=cursor,endTime=end,limit=1000));url=BI+'?'+q;p=cache/f'XRPUSDT-1d-api-{page}.json';raw=get(url,p);doc=json.loads(raw);man.append(dict(kind='binance_XRPUSDT_1d',url=url,cache_file=p.name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),rows=len(doc)))
        if not doc:break
        rows += [dict(timestamp=int(x[0]),open=float(x[1]),high=float(x[2]),low=float(x[3]),close=float(x[4])) for x in doc];cursor=int(doc[-1][0])+DAY;page+=1
        if len(doc)<1000:break
    return rows,man
def metrics(t,c,initial=10000.):
    w=sum(max(0,x['pnl']) for x in t);l=-sum(min(0,x['pnl']) for x in t);n=sum(x['pnl'] for x in t);peak=initial;dd=0
    for x in c:peak=max(peak,x['equity']);dd=max(dd,(peak-x['equity'])/peak*100)
    return dict(trades=len(t),net_pnl=n,net_return_pct=n/initial*100,profit_factor=w/l if l else None,expectancy=n/len(t) if t else None,max_drawdown_pct=dd,fees=sum(x['fees'] for x in t),slippage_cost=sum(x['slippage_cost'] for x in t),gross_profit=w,gross_loss=l)
def main():
    cache=pathlib.Path(sys.argv[1]);dest=pathlib.Path(sys.argv[2]);cache.mkdir(parents=True,exist_ok=True);dest.mkdir(parents=True,exist_ok=True);mr,mm=load_metric(cache);rows,pm=load_prices(cache);validate(rows);signals=make_signals(mr)
    for x in rows:
        if x['timestamp'] in signals:x['hashrate_signal']=signals[x['timestamp']]
    folds=[('2021_control',stamp(2021),stamp(2022))]+[(str(y),stamp(y),stamp(y+1) if y<2026 else stamp(2026,10)) for y in range(2022,2027)]+[('continuous_oos',stamp(2022),stamp(2026,10))];runs={};ledgers={}
    for name,start,end in folds:
        for label,mul in (('base',1),('stress',2)):
            c=replace(Config(),fee=Config().fee*mul,slippage=Config().slippage*mul);t,curve=backtest(rows,start,end,c);key=name+'_'+label;ledgers[key]=t;runs[key]=metrics(t,curve);print(key,runs[key],flush=True)
    years=[str(y) for y in range(2022,2027)];base=[x for y in years for x in ledgers[y+'_base']];stress=[x for y in years for x in ledgers[y+'_stress']];agg=metrics(base,[]);aggs=metrics(stress,[]);agg['max_drawdown_pct']=None;aggs['max_drawdown_pct']=None;by={y:runs[y+'_base']['net_pnl'] for y in years};bys={y:runs[y+'_stress']['net_pnl'] for y in years};monthly={}
    for x in base:
        k=dt.datetime.fromtimestamp(x['exit_timestamp']/1000,UTC).strftime('%Y-%m');monthly[k]=monthly.get(k,0)+x['pnl']
    positive=sum(max(0,v) for v in monthly.values());share=max((max(0,v)/positive for v in monthly.values()),default=1)
    gates=dict(sample=agg['trades']>=120,base_net=agg['net_pnl']>0,base_expectancy=(agg['expectancy'] or 0)>0,base_pf=(agg['profit_factor'] or 0)>1.20,stress_net=aggs['net_pnl']>0,stress_expectancy=(aggs['expectancy'] or 0)>0,stress_pf=(aggs['profit_factor'] or 0)>1.05,four_years=sum(v>0 for v in by.values())>=4,four_years_stress=sum(v>0 for v in bys.values())>=4,final_year=by['2026']>0 and bys['2026']>0,drawdown=max(runs['continuous_oos_base']['max_drawdown_pct'],runs['continuous_oos_stress']['max_drawdown_pct'])<=10,concentration=agg['net_pnl']>0 and positive>0 and share<=.25,audit=False,forward_paper=False)
    hist=all(v for k,v in gates.items() if k not in ('audit','forward_paper'));proto=pathlib.Path('research/btc_hashrate_shock_recovery_protocol_20261030.md');sig_by={str(y):sum(dt.datetime.fromtimestamp(t/1000,UTC).year==y for t in signals) for y in range(2021,2027)}
    res=dict(strategy='BTC_HASHRATE_SHOCK_RECOVERY_XRP_V1',status='TEST NEDOKONCEN: audit and forward PAPER required' if hist else 'NEPROSEL',protocol_sha256=hashlib.sha256(proto.read_bytes()).hexdigest(),manifest=[mm]+pm,data_quality=dict(metric_rows=len(mr),metric_start=mr[0]['timestamp'],metric_end=mr[-1]['timestamp'],metric_gaps=[],price_rows=len(rows),price_start=rows[0]['timestamp'],price_end=rows[-1]['timestamp'],price_gaps=[]),signals_total=len(signals),signals_by_entry_year=sig_by,runs=runs,aggregate_oos=agg,aggregate_stress=aggs,by_year=by,stress_by_year=bys,monthly_base=monthly,positive_month_profit_concentration=share,gates=gates,historical_pass_before_audit=hist,limitations=['Daily hashrate is an estimate from block production and can be revised.','A one-standard-deviation shortfall can reflect sampling noise rather than miner capitulation.','Daily XRP OHLC cannot reconstruct tick paths; fixed conservative gap/stop rules apply.','Local SHA256 values are not publisher signatures.','No independent forward PAPER evidence exists.']);(dest/'results.json').write_text(json.dumps(res,indent=2,allow_nan=False)+'\n')
    with gzip.open(dest/'trades.json.gz','wt') as h:json.dump(ledgers,h)
    print(res['status'],gates,sig_by,flush=True)
if __name__=='__main__':main()
