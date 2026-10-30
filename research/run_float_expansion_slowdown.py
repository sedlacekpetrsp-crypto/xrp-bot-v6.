import csv,datetime as dt,gzip,hashlib,io,json,pathlib,sys,urllib.request,zipfile
from dataclasses import replace
from research.float_expansion_slowdown_v1 import Config,DAY,backtest,make_signals,validate_prices
UTC=dt.timezone.utc;MONTHS=[(y,m) for y in range(2020,2027) for m in range(1,13) if (y,m)<(2026,10)]
URL='https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=xrp&metrics=CapMrktEstUSD%2CCapMrktCurUSD&frequency=1d&page_size=10000'
def get(url,p):
    if not p.exists():
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'xrp-research/1.0'}),timeout=120) as r:p.write_bytes(r.read())
    return p.read_bytes()
def stamp(y,m=1):return int(dt.datetime(y,m,1,tzinfo=UTC).timestamp()*1000)
def metric(cache):
    p=cache/'cm-xrp-float-caps.json';raw=get(URL,p);doc=json.loads(raw);rows=[]
    for x in doc['data']:
        if not x.get('CapMrktEstUSD') or not x.get('CapMrktCurUSD'):continue
        t=int(dt.datetime.fromisoformat(x['time'].replace('Z','+00:00')).timestamp()*1000);rows.append(dict(timestamp=t,estimated_cap=float(x['CapMrktEstUSD']),current_cap=float(x['CapMrktCurUSD'])))
    return rows,dict(kind='coinmetrics_xrp_CapMrktEstUSD_CapMrktCurUSD',url=URL,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),raw_rows=len(doc['data']),rows=len(rows),excluded_null=len(doc['data'])-len(rows))
def prices(cache):
    out=[];man=[]
    for y,m in MONTHS:
        n=f'XRPUSDT-1d-{y}-{m:02d}.zip';u=f'https://data.binance.vision/data/spot/monthly/klines/XRPUSDT/1d/{n}';p=cache/n;raw=get(u,p)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:source=csv.reader(io.TextIOWrapper(z.open(z.namelist()[0])))
        k=0
        for x in source:
            if x[0].lower().startswith('open'):continue
            t=int(x[0]);t=t//1000 if t>10**14 else t;out.append(dict(timestamp=t,open=float(x[1]),high=float(x[2]),low=float(x[3]),close=float(x[4])));k+=1
        man.append(dict(kind='binance_XRPUSDT_1d',url=u,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),rows=k))
    return out,man
def uniq(rows,name):
    d={};dups=0
    for x in rows:
        if x['timestamp'] in d:
            if d[x['timestamp']]!=x:raise ValueError(name+' conflict')
            dups+=1
        d[x['timestamp']]=x
    return [d[t] for t in sorted(d)],dups
def metrics(t,c,initial=10000.):
    g=sum(max(0,x['pnl']) for x in t);l=-sum(min(0,x['pnl']) for x in t);n=sum(x['pnl'] for x in t);peak=initial;dd=0
    for x in c:peak=max(peak,x['equity']);dd=max(dd,(peak-x['equity'])/peak*100)
    return dict(trades=len(t),net_pnl=n,net_return_pct=n/initial*100,profit_factor=g/l if l else None,expectancy=n/len(t) if t else None,max_drawdown_pct=dd,fees=sum(x['fees'] for x in t),slippage_cost=sum(x['slippage_cost'] for x in t))
def gaps(rows):return [dict(after=a['timestamp'],before=b['timestamp'],missing_days=(b['timestamp']-a['timestamp'])//DAY-1) for a,b in zip(rows,rows[1:]) if b['timestamp']-a['timestamp']!=DAY]
def main():
    cache=pathlib.Path(sys.argv[1]);cache.mkdir(parents=True,exist_ok=True);dest=pathlib.Path(sys.argv[2]);dest.mkdir(parents=True,exist_ok=True);mr,mm=metric(cache);mr,mdup=uniq(mr,'metric');raw,pm=prices(cache);rows,pdup=uniq(raw,'price');validate_prices(rows)
    if gaps(mr):raise ValueError('metric gap')
    signals=make_signals(mr)
    for x in rows:
        if x['timestamp'] in signals:x['float_signal']=signals[x['timestamp']]
    folds=[('2021_control',stamp(2021),stamp(2022))]+[(str(y),stamp(y),stamp(y+1) if y<2026 else stamp(2026,10)) for y in range(2022,2027)]+[('continuous_oos',stamp(2022),stamp(2026,10))];runs={};ledgers={}
    for name,start,end in folds:
        for label,mul in (('base',1),('stress',2)):
            c=replace(Config(),fee=Config().fee*mul,slippage=Config().slippage*mul);t,curve=backtest(rows,start,end,c);key=f'{name}_{label}';ledgers[key]=t;runs[key]=metrics(t,curve);print(key,runs[key],flush=True)
    years=[str(y) for y in range(2022,2027)];base=[x for y in years for x in ledgers[y+'_base']];stress=[x for y in years for x in ledgers[y+'_stress']];agg=metrics(base,[{'equity':10000},{'equity':10000+sum(x['pnl'] for x in base)}]);aggs=metrics(stress,[{'equity':10000},{'equity':10000+sum(x['pnl'] for x in stress)}]);agg['max_drawdown_pct']=None;aggs['max_drawdown_pct']=None
    by={y:runs[y+'_base']['net_pnl'] for y in years};bys={y:runs[y+'_stress']['net_pnl'] for y in years};monthly={}
    for x in base:
        k=dt.datetime.fromtimestamp(x['exit_timestamp']/1000,UTC).strftime('%Y-%m');monthly[k]=monthly.get(k,0)+x['pnl']
    pos=sum(max(0,v) for v in monthly.values());gates=dict(sample=agg['trades']>=120,base_net=agg['net_pnl']>0,base_expectancy=(agg['expectancy'] or 0)>0,base_pf=(agg['profit_factor'] or 0)>1.20,stress_net=aggs['net_pnl']>0,stress_expectancy=(aggs['expectancy'] or 0)>0,stress_pf=(aggs['profit_factor'] or 0)>1.05,four_years=sum(v>0 for v in by.values())>=4,four_years_stress=sum(v>0 for v in bys.values())>=4,final_year=by['2026']>0 and bys['2026']>0,drawdown=max(runs['continuous_oos_base']['max_drawdown_pct'],runs['continuous_oos_stress']['max_drawdown_pct'])<=10,concentration=agg['net_pnl']>0 and pos>0 and max(monthly.values(),default=0)<=.25*pos,audit=False,forward_paper=False)
    hist=all(v for k,v in gates.items() if k not in ('audit','forward_paper'));proto=pathlib.Path('research/float_expansion_slowdown_protocol_20261030.md');res=dict(strategy='XRP_FLOAT_EXPANSION_SLOWDOWN_V1',status='TEST NEDOKONCEN: audit and forward PAPER required' if hist else 'NEPROSEL',protocol_sha256=hashlib.sha256(proto.read_bytes()).hexdigest(),manifest=[mm]+pm,data_quality=dict(metric_rows=len(mr),metric_duplicates=mdup,metric_start=mr[0]['timestamp'],metric_end=mr[-1]['timestamp'],metric_gaps=gaps(mr),price_rows=len(rows),price_duplicates=pdup,price_start=rows[0]['timestamp'],price_end=rows[-1]['timestamp'],price_gaps=gaps(rows),eligible_signal_days=len(signals)),runs=runs,aggregate_oos=agg,aggregate_stress=aggs,by_year=by,stress_by_year=bys,monthly_base=monthly,gates=gates,historical_pass_before_audit=hist,limitations=['CoinMetrics estimated supply methodology and history can revise; retained hashes are local.','The capitalization ratio cancels the shared reported price but depends on CoinMetrics estimated-supply methodology.','A low relative expansion pace is not proof of escrow flows or market selling.','Daily OHLC cannot reconstruct intraday paths; stop-first and gap-stop rules apply.','No independent forward PAPER evidence exists.']);(dest/'results.json').write_text(json.dumps(res,indent=2,allow_nan=False)+'\n')
    with gzip.open(dest/'trades.json.gz','wt') as h:json.dump(ledgers,h)
    print(res['status'],gates,flush=True)
if __name__=='__main__':main()
