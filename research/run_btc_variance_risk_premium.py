import csv,datetime as dt,gzip,hashlib,io,json,pathlib,sys,urllib.request,zipfile
from dataclasses import replace
from research.btc_variance_risk_premium_v1 import Config,DAY,backtest,make_signals,validate_prices
UTC=dt.timezone.utc;START=1614556800000;END=1790812799999
MONTHS=[(y,m) for y in range(2020,2027) for m in range(1,13) if (y,m)<(2026,10)]
def get(url,p):
    if not p.exists():
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'xrp-research/1.0'}),timeout=120) as r:p.write_bytes(r.read())
    return p.read_bytes()
def stamp(y,m=1):return int(dt.datetime(y,m,1,tzinfo=UTC).timestamp()*1000)
def dvol(cache):
    rows=[];manifest=[];end=END;page=1
    while True:
        url=f'https://www.deribit.com/api/v2/public/get_volatility_index_data?currency=BTC&start_timestamp={START}&end_timestamp={end}&resolution=86400';p=cache/f'deribit-btc-dvol-p{page}.json';raw=get(url,p);doc=json.loads(raw);result=doc['result'];data=result['data']
        manifest.append(dict(kind='deribit_BTC_DVOL_1d',page=page,url=url,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),rows=len(data)))
        rows += [dict(timestamp=int(x[0]),open=float(x[1]),high=float(x[2]),low=float(x[3]),close=float(x[4])) for x in data]
        cont=result.get('continuation')
        if cont is None:break
        if cont>=end:raise ValueError('pagination did not retreat')
        end=int(cont);page+=1
    d={}
    for x in rows:
        if x['timestamp'] in d and d[x['timestamp']]!=x:raise ValueError('DVOL conflict')
        d[x['timestamp']]=x
    out=[d[t] for t in sorted(d)]
    for x in out:
        if x['timestamp']%DAY or not 0<x['low']<=min(x['open'],x['close'])<=max(x['open'],x['close'])<=x['high']:raise ValueError('DVOL value')
    return out,manifest,len(rows)-len(out)
def prices(cache,symbol):
    out=[];manifest=[]
    for y,m in MONTHS:
        name=f'{symbol}-1d-{y}-{m:02d}.zip';url=f'https://data.binance.vision/data/spot/monthly/klines/{symbol}/1d/{name}';p=cache/name;raw=get(url,p)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:source=list(csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]))))
        n=0
        for x in source:
            if x[0].lower().startswith('open'):continue
            t=int(x[0]);t=t//1000 if t>10**14 else t;out.append(dict(timestamp=t,open=float(x[1]),high=float(x[2]),low=float(x[3]),close=float(x[4])));n+=1
        manifest.append(dict(kind=f'binance_{symbol}_1d',url=url,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),rows=n))
    d={};dups=0
    for x in out:
        if x['timestamp'] in d:
            if d[x['timestamp']]!=x:raise ValueError('price conflict')
            dups+=1
        d[x['timestamp']]=x
    rows=[d[t] for t in sorted(d)];validate_prices(rows);return rows,manifest,dups
def metrics(t,c,initial=10000.):
    g=sum(max(0,x['pnl']) for x in t);l=-sum(min(0,x['pnl']) for x in t);n=sum(x['pnl'] for x in t);peak=initial;dd=0
    for x in c:peak=max(peak,x['equity']);dd=max(dd,(peak-x['equity'])/peak*100)
    return dict(trades=len(t),net_pnl=n,net_return_pct=n/initial*100,profit_factor=g/l if l else None,expectancy=n/len(t) if t else None,max_drawdown_pct=dd,fees=sum(x['fees'] for x in t),slippage_cost=sum(x['slippage_cost'] for x in t))
def gaps(rows):return [dict(after=a['timestamp'],before=b['timestamp'],missing_days=(b['timestamp']-a['timestamp'])//DAY-1) for a,b in zip(rows,rows[1:]) if b['timestamp']-a['timestamp']!=DAY]
def main():
    cache=pathlib.Path(sys.argv[1]);cache.mkdir(parents=True,exist_ok=True);dest=pathlib.Path(sys.argv[2]);dest.mkdir(parents=True,exist_ok=True)
    dv,dm,ddup=dvol(cache)
    if gaps(dv):raise ValueError('DVOL calendar gap')
    btc,bm,bdup=prices(cache,'BTCUSDT');xrp,xm,xdup=prices(cache,'XRPUSDT');signals=make_signals(dv,btc)
    for x in xrp:
        if x['timestamp'] in signals:x['vrp_signal']=signals[x['timestamp']]
    folds=[('2021_control',stamp(2021,4),stamp(2022))]+[(str(y),stamp(y),stamp(y+1) if y<2026 else stamp(2026,10)) for y in range(2022,2027)]+[('continuous_oos',stamp(2022),stamp(2026,10))];runs={};ledgers={}
    for name,start,end in folds:
        for label,mul in (('base',1),('stress',2)):
            c=replace(Config(),fee=Config().fee*mul,slippage=Config().slippage*mul);t,curve=backtest(xrp,start,end,c);key=f'{name}_{label}';ledgers[key]=t;runs[key]=metrics(t,curve);print(key,runs[key],flush=True)
    years=[str(y) for y in range(2022,2027)];base=[x for y in years for x in ledgers[y+'_base']];stress=[x for y in years for x in ledgers[y+'_stress']];agg=metrics(base,[{'equity':10000},{'equity':10000+sum(x['pnl'] for x in base)}]);aggs=metrics(stress,[{'equity':10000},{'equity':10000+sum(x['pnl'] for x in stress)}]);agg['max_drawdown_pct']=None;aggs['max_drawdown_pct']=None
    by={y:runs[y+'_base']['net_pnl'] for y in years};bys={y:runs[y+'_stress']['net_pnl'] for y in years};monthly={}
    for x in base:
        k=dt.datetime.fromtimestamp(x['exit_timestamp']/1000,UTC).strftime('%Y-%m');monthly[k]=monthly.get(k,0)+x['pnl']
    pos=sum(max(0,v) for v in monthly.values());gates=dict(sample=agg['trades']>=100,base_net=agg['net_pnl']>0,base_expectancy=(agg['expectancy'] or 0)>0,base_pf=(agg['profit_factor'] or 0)>1.20,stress_net=aggs['net_pnl']>0,stress_expectancy=(aggs['expectancy'] or 0)>0,stress_pf=(aggs['profit_factor'] or 0)>1.05,four_years=sum(v>0 for v in by.values())>=4,four_years_stress=sum(v>0 for v in bys.values())>=4,final_year=by['2026']>0 and bys['2026']>0,drawdown=max(runs['continuous_oos_base']['max_drawdown_pct'],runs['continuous_oos_stress']['max_drawdown_pct'])<=10,concentration=agg['net_pnl']>0 and pos>0 and max(monthly.values(),default=0)<=.25*pos,audit=False,forward_paper=False)
    hist=all(v for k,v in gates.items() if k not in ('audit','forward_paper'));proto=pathlib.Path('research/btc_variance_risk_premium_protocol_20261030.md');result=dict(strategy='BTC_VARIANCE_RISK_PREMIUM_XRP_V1',status='TEST NEDOKONCEN: audit and forward PAPER required' if hist else 'NEPROSEL',protocol_sha256=hashlib.sha256(proto.read_bytes()).hexdigest(),manifest=dm+bm+xm,data_quality=dict(dvol_rows=len(dv),dvol_duplicates=ddup,dvol_start=dv[0]['timestamp'],dvol_end=dv[-1]['timestamp'],dvol_gaps=gaps(dv),btc_rows=len(btc),btc_duplicates=bdup,btc_gaps=gaps(btc),xrp_rows=len(xrp),xrp_duplicates=xdup,xrp_gaps=gaps(xrp),eligible_signal_days=len(signals)),runs=runs,aggregate_oos=agg,aggregate_stress=aggs,by_year=by,stress_by_year=bys,monthly_base=monthly,gates=gates,historical_pass_before_audit=hist,limitations=['DVOL is a third-party official Deribit index response and historical payloads can revise; hashes are local.','Daily DVOL close publication timing is conservatively delayed by an extra full day.','The 15-point threshold is fixed but not derived from XRP; market-regime dependence remains possible.','Daily XRP OHLC is not tick execution; stop-first and gap-stop approximations apply.','No independent forward PAPER evidence exists.']);(dest/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    with gzip.open(dest/'trades.json.gz','wt') as h:json.dump(ledgers,h)
    print(result['status'],gates,flush=True)
if __name__=='__main__':main()
