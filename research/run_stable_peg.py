"""Provenance-preserving multi-stablecoin chronological evaluation."""
import concurrent.futures,csv,gzip,hashlib,io,json,pathlib,sys,urllib.request,zipfile
from dataclasses import replace
from research.stable_peg_v1 import Config,backtest,validate
from research.run_autocorr_history import metrics,stamp
SYMBOLS=('USDCUSDT','FDUSDUSDT','TUSDUSDT')
def fetch(job):
    s,y,m,cache=job;name=f'{s}-15m-{y}-{m:02d}.zip';path=cache/name;url=f'https://data.binance.vision/data/spot/monthly/klines/{s}/15m/{name}'
    if not path.exists():
        with urllib.request.urlopen(url,timeout=45) as r:path.write_bytes(r.read())
    payload=path.read_bytes()
    with zipfile.ZipFile(io.BytesIO(payload)) as z:rows=list(csv.reader(io.TextIOWrapper(z.open(name[:-4]+'.csv'))))
    bars=[]
    for r in rows:
        t=int(r[0]);t=t//1000 if t>10**14 else t;bars.append(dict(timestamp=t,open=float(r[1]),high=float(r[2]),low=float(r[3]),close=float(r[4])))
    validate(bars);start=stamp(y,m);finish=stamp(y+1,1) if m==12 else stamp(y,m+1)
    if bars[0]['timestamp']!=start or bars[-1]['timestamp']!=finish-900000 or len(bars)!=(finish-start)//900000:raise ValueError('monthly coverage')
    return s,bars,dict(url=url,sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload),bars=len(bars))
def agg(ts):
    w=sum(max(0,t['pnl']) for t in ts);l=-sum(min(0,t['pnl']) for t in ts);return dict(trades=len(ts),net_pnl=w-l,profit_factor=w/l if l else None,expectancy=(w-l)/len(ts) if ts else None)
def main():
    cache=pathlib.Path(sys.argv[1]);cache.mkdir(parents=True,exist_ok=True);dest=pathlib.Path(sys.argv[2]);dest.mkdir(parents=True,exist_ok=True)
    months=[(y,m) for y in range(2024,2027) for m in range(1,13) if (y,m)<(2026,10)];jobs=[(s,y,m,cache) for s in SYMBOLS for y,m in months];markets={s:[] for s in SYMBOLS};manifest=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as p:
        for n,(s,b,src) in enumerate(p.map(fetch,jobs),1):markets[s]+=b;manifest.append(src);print('archives',n,'/',len(jobs),flush=True) if n%24==0 else None
    folds=[('2024_control',stamp(2024,1),stamp(2025,1)),('2025Q1',stamp(2025,1),stamp(2025,4)),('2025Q2',stamp(2025,4),stamp(2025,7)),('2025Q3',stamp(2025,7),stamp(2025,10)),('2025Q4',stamp(2025,10),stamp(2026,1)),('2026Q1',stamp(2026,1),stamp(2026,4)),('2026Q2',stamp(2026,4),stamp(2026,7)),('2026Q3',stamp(2026,7),stamp(2026,10)),('continuous_oos',stamp(2025,1),stamp(2026,10))]
    runs={};ledger={};initial=10000/3
    for s in SYMBOLS:
      for name,start,end in folds:
       for cost,mult in [('base',1),('stress',2)]:
        c=replace(Config(),fee=.00095*mult,slippage=.0002*mult);ts=backtest(markets[s],start,end,c,initial);key=f'{s}_{name}_{cost}';runs[key]=metrics(markets[s],ts,initial,c);runs[key]['slippage_cost']=sum(t['slippage_cost'] for t in ts);ledger[key]=[dict(t,symbol=s,entry_timestamp=markets[s][t['entry_index']]['timestamp'],exit_timestamp=markets[s][t['exit_index']]['timestamp']) for t in ts]
    qs=('2025Q1','2025Q2','2025Q3','2025Q4','2026Q1','2026Q2','2026Q3');base=[t for s in SYMBOLS for q in qs for t in ledger[f'{s}_{q}_base']];stress=[t for s in SYMBOLS for q in qs for t in ledger[f'{s}_{q}_stress']];a,b=agg(base),agg(stress)
    sym={s:agg([t for q in qs for t in ledger[f'{s}_{q}_base']]) for s in SYMBOLS};syms={s:agg([t for q in qs for t in ledger[f'{s}_{q}_stress']]) for s in SYMBOLS};quarter={q:sum(runs[f'{s}_{q}_base']['net_pnl'] for s in SYMBOLS) for q in qs}
    cont_base=sum(runs[f'{s}_continuous_oos_base']['net_pnl'] for s in SYMBOLS);cont_stress=sum(runs[f'{s}_continuous_oos_stress']['net_pnl'] for s in SYMBOLS)
    gates=dict(sample=a['trades']>=90,base_net=a['net_pnl']>0,base_expectancy=(a['expectancy'] or 0)>0,base_pf=(a['profit_factor'] or 0)>1.15,stress_net=b['net_pnl']>0,stress_expectancy=(b['expectancy'] or 0)>0,stress_pf=(b['profit_factor'] or 0)>1.02,all_symbols=all(sym[s]['net_pnl']>0 and syms[s]['net_pnl']>0 for s in SYMBOLS),five_positive_quarters=sum(v>0 for v in quarter.values())>=5,final_quarter=quarter['2026Q3']>0,drawdown=all(runs[f'{s}_continuous_oos_{x}']['max_drawdown_pct']<=10 for s in SYMBOLS for x in ('base','stress')),concentration=a['net_pnl']>0 and max([v for v in quarter.values()]+[v['net_pnl'] for v in sym.values()])<=.5*a['net_pnl'])
    p=pathlib.Path('research/stable_peg_protocol.md');result=dict(strategy='MULTI_STABLE_PEG_REVERSION_V1',status='NEPROSEL' if not all(gates.values()) else 'TEST NEDOKONCEN: forward evidence required',protocol=str(p),protocol_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),manifest=manifest,runs=runs,aggregate_oos=a,aggregate_stress=b,by_symbol=sym,by_symbol_stress=syms,by_quarter=quarter,continuous_portfolio_net=dict(base=cont_base,stress=cont_stress),gates=gates,limitations=['Exploratory history.','Local SHA256 are not publisher signatures.','Isolated equal sleeves; no cross-sleeve reallocation.','OHLC path/drawdown not tick-exact.','No forward PAPER evidence.'])
    (dest/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');
    with gzip.open(dest/'trades.json.gz','wt') as f:json.dump(ledger,f)
    print(result['status'],json.dumps(gates),flush=True)
if __name__=='__main__':main()
