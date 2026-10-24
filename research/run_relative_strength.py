"""Download provenance-checked hourly archives and run frozen chronological folds."""
import concurrent.futures,csv,gzip,hashlib,io,json,pathlib,sys,urllib.request,zipfile
from dataclasses import replace
from research.relative_strength_v1 import backtest,validate,Config
from research.run_autocorr_history import stamp,metrics

def fetch(job):
    s,y,m,cache=job;name=f'{s}-1h-{y}-{m:02d}.zip';path=cache/name
    url=f'https://data.binance.vision/data/spot/monthly/klines/{s}/1h/{name}'
    if not path.exists():
        with urllib.request.urlopen(url,timeout=45) as r:payload=r.read()
        path.write_bytes(payload)
    payload=path.read_bytes()
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        if z.namelist()!=[name[:-4]+'.csv']:raise ValueError('ZIP members')
        rows=list(csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]))))
    bars=[]
    for r in rows:
        t=int(r[0]);t=t//1000 if t>10**14 else t
        bars.append(dict(timestamp=t,**dict(zip(('open','high','low','close'),map(float,r[1:5])))))
    start=stamp(y,m);end=stamp(y+1,1) if m==12 else stamp(y,m+1)
    times=[b['timestamp'] for b in bars]
    if not times or times[0]!=start or times[-1]!=end-3600000 or any(t<start or t>=end or t%3600000 for t in times) or any(b<=a for a,b in zip(times,times[1:])):raise ValueError('Malformed archive')
    missing=sorted(set(range(start,end,3600000))-set(times))
    return s,bars,dict(url=url,sha256=hashlib.sha256(payload).hexdigest(),bars=len(bars),missing_timestamps=missing)

def main():
    cache=pathlib.Path(sys.argv[1]);cache.mkdir(parents=True,exist_ok=True)
    dest=pathlib.Path(sys.argv[2]);dest.mkdir(parents=True,exist_ok=True)
    months=[(y,m) for y in range(2022,2027) for m in range(1,13) if (y,m)<(2026,10)]
    jobs=[(s,y,m,cache) for s in ('XRPUSDT','BTCUSDT','ETHUSDT') for y,m in months]
    markets={s:[] for s in ('XRPUSDT','BTCUSDT','ETHUSDT')};manifest=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for n,(s,bars,source) in enumerate(pool.map(fetch,jobs),1):
            markets[s]+=bars;manifest.append(source)
            if n%12==0:print('Validated archives',n,'/',len(jobs),flush=True)
    common=set.intersection(*(set(b['timestamp'] for b in bars) for bars in markets.values()))
    omitted={s:[b['timestamp'] for b in bars if b['timestamp'] not in common] for s,bars in markets.items()}
    markets={s:[b for b in bars if b['timestamp'] in common] for s,bars in markets.items()}
    validate(markets);bars=markets['XRPUSDT'];runs={};ledger={}
    folds=[(str(y),stamp(y,1),stamp(y+1,1) if y<2026 else stamp(2026,10)) for y in range(2022,2027)]
    folds.append(('continuous_oos',stamp(2023,1),stamp(2026,10)))
    for name,start,end in folds:
        for label,mult in [('base',1),('stress',2)]:
            c=replace(Config(),fee=.00095*mult,slippage=.0002*mult)
            ts=backtest(markets,start,end,c);key=f'{name}_{label}'
            r=metrics(bars,ts,10000,c)
            r['slippage_cost']=sum(t['slippage_cost'] for t in ts)
            period=[b for b in bars if start<=b['timestamp']<end]
            buy=period[0]['open']*(1+c.slippage);sell=period[-1]['close']*(1-c.slippage)
            r['buy_hold_20pct_net_pnl']=2000/buy*(sell-buy)-c.fee*2000/buy*(buy+sell)
            runs[key]=r;ledger[key]=[dict(t,entry_timestamp=bars[t['entry_index']]['timestamp'],exit_timestamp=bars[t['exit_index']]['timestamp']) for t in ts]
            print(key,json.dumps(r),flush=True)
    oos=[t for y in range(2023,2027) for t in ledger[f'{y}_base']]
    stress=[t for y in range(2023,2027) for t in ledger[f'{y}_stress']]
    def aggregate(ts):
        pos=sum(max(0,t['pnl']) for t in ts);neg=-sum(min(0,t['pnl']) for t in ts)
        return dict(trades=len(ts),net_pnl=pos-neg,pf=pos/neg if neg else None)
    a,b=aggregate(oos),aggregate(stress);monthly={}
    for y in range(2023,2027):
        for month,pnl in runs[f'{y}_base']['monthly_net'].items():monthly[month]=pnl
    gates=dict(sample=a['trades']>=100,base_pf=(a['pf'] or 0)>1.2,base_net=a['net_pnl']>0,three_positive_folds=sum(runs[f'{y}_base']['net_pnl']>0 for y in range(2023,2027))>=3,final_fold=runs['2026_base']['net_pnl']>0,stress_pf=(b['pf'] or 0)>1.05,stress_net=b['net_pnl']>0,drawdown=all(runs[f'continuous_oos_{cost}']['max_drawdown_pct']<=10 for cost in ('base','stress')),concentration=a['net_pnl']>0 and max(monthly.values(),default=0)<=.5*a['net_pnl'])
    result=dict(strategy='XRP_RELATIVE_STRENGTH_V1',status='NEPROSEL' if not all(gates.values()) else 'TEST NEDOKONCEN: forward evidence required',protocol='research/relative_strength_protocol.md',protocol_sha256=hashlib.sha256(pathlib.Path('research/relative_strength_protocol.md').read_bytes()).hexdigest(),manifest=manifest,alignment_omissions=omitted,runs=runs,aggregate_oos=a,aggregate_stress=b,gates=gates,limitations=['Exploratory repeatedly inspected history; not untouched validation.','Computed SHA256 fingerprints are not independently publisher-verified.','OHLC conservative liquidation drawdown, not tick-exact.','No independent future PAPER observations.'])
    (dest/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    with gzip.open(dest/'trades.json.gz','wt') as f:json.dump(ledger,f)
    print(result['status'],gates,flush=True)
if __name__=='__main__':main()
