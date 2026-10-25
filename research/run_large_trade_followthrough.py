"""Real Binance archive runner retaining quote volume and trade count."""
import concurrent.futures,csv,gzip,hashlib,io,json,pathlib,sys,urllib.request,zipfile
from dataclasses import replace
from research.large_trade_followthrough_v1 import Config,backtest,validate
from research.run_autocorr_history import metrics,stamp
def fetch(job):
    y,m,cache=job;name=f'XRPUSDT-1h-{y}-{m:02d}.zip';path=cache/name;url=f'https://data.binance.vision/data/spot/monthly/klines/XRPUSDT/1h/{name}'
    if not path.exists():
        with urllib.request.urlopen(url,timeout=45) as r:path.write_bytes(r.read())
    payload=path.read_bytes()
    with zipfile.ZipFile(io.BytesIO(payload)) as z:rows=list(csv.reader(io.TextIOWrapper(z.open(name[:-4]+'.csv'))))
    bars=[]
    for r in rows:
        t=int(r[0]);t=t//1000 if t>10**14 else t;bars.append(dict(timestamp=t,open=float(r[1]),high=float(r[2]),low=float(r[3]),close=float(r[4]),quote_volume=float(r[7]),trades=float(r[8])))
    return bars,dict(url=url,sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload),bars=len(bars))
def agg(ts):
    w=sum(max(0,t['pnl']) for t in ts);l=-sum(min(0,t['pnl']) for t in ts);return dict(trades=len(ts),net_pnl=w-l,profit_factor=w/l if l else None,expectancy=(w-l)/len(ts) if ts else None)
def main():
    cache=pathlib.Path(sys.argv[1]);cache.mkdir(parents=True,exist_ok=True);dest=pathlib.Path(sys.argv[2]);dest.mkdir(parents=True,exist_ok=True)
    jobs=[(y,m,cache) for y in range(2022,2027) for m in range(1,13) if (y,m)<(2026,10)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as p:chunks=list(p.map(fetch,jobs))
    bars=[b for x,_ in chunks for b in x];validate(bars);runs={};ledger={}
    folds=[('2022_control',stamp(2022,1),stamp(2023,1))]+[(str(y),stamp(y,1),stamp(y+1,1) if y<2026 else stamp(2026,10)) for y in range(2023,2027)]+[('continuous_oos',stamp(2023,1),stamp(2026,10))]
    for name,start,end in folds:
        for cost,mult in [('base',1),('stress',2)]:
            c=replace(Config(),fee=.00095*mult,slippage=.0002*mult);ts=backtest(bars,start,end,c);key=f'{name}_{cost}';runs[key]=metrics(bars,ts,10000,c);runs[key]['slippage_cost']=sum(t['slippage_cost'] for t in ts);ledger[key]=[dict(t,entry_timestamp=bars[t['entry_index']]['timestamp'],exit_timestamp=bars[t['exit_index']]['timestamp']) for t in ts];print(key,json.dumps(runs[key]),flush=True)
    base=[t for y in range(2023,2027) for t in ledger[f'{y}_base']];stress=[t for y in range(2023,2027) for t in ledger[f'{y}_stress']];a,b=agg(base),agg(stress);monthly={}
    for y in range(2023,2027):
        for k,v in runs[f'{y}_base']['monthly_net'].items():monthly[k]=v
    gates=dict(sample=a['trades']>=150,base_net=a['net_pnl']>0,base_expectancy=(a['expectancy'] or 0)>0,base_pf=(a['profit_factor'] or 0)>1.15,stress_net=b['net_pnl']>0,stress_expectancy=(b['expectancy'] or 0)>0,stress_pf=(b['profit_factor'] or 0)>1.02,three_positive_folds=sum(runs[f'{y}_base']['net_pnl']>0 for y in range(2023,2027))>=3,final_fold=runs['2026_base']['net_pnl']>0,drawdown=all(runs[f'continuous_oos_{x}']['max_drawdown_pct']<=10 for x in ('base','stress')),concentration=a['net_pnl']>0 and max(monthly.values(),default=0)<=.4*a['net_pnl'])
    p=pathlib.Path('research/large_trade_followthrough_protocol.md');result=dict(strategy='XRP_LARGE_TRADE_FOLLOWTHROUGH_V1',status='NEPROSEL' if not all(gates.values()) else 'TEST NEDOKONCEN: forward evidence required',protocol=str(p),protocol_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),manifest=[x for _,x in chunks],runs=runs,aggregate_oos=a,aggregate_stress=b,gates=gates,limitations=['Exploratory reused history.','Local SHA256 are not publisher signatures.','OHLC path/drawdown not tick-exact.','No forward PAPER evidence.'])
    (dest/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');
    with gzip.open(dest/'trades.json.gz','wt') as f:json.dump(ledger,f)
    print(result['status'],json.dumps(gates),flush=True)
if __name__=='__main__':main()
