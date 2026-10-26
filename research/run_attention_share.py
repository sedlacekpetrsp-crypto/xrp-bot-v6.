"""Download fixed-basket Binance spot data and run the frozen screen."""
import concurrent.futures,csv,datetime as dt,gzip,hashlib,io,json,pathlib,sys,urllib.request,zipfile
from dataclasses import replace
from research.attention_share_v1 import ASSETS,Config,STEP,backtest,validate
from research.run_autocorr_history import metrics as score,stamp
MONTHS=[(y,m) for y in range(2022,2027) for m in range(1,13) if (y,m)<(2026,10)]
def fetch(job):
    a,y,m,cache=job; name=f'{a}-1h-{y}-{m:02d}.zip'; url=f'https://data.binance.vision/data/spot/monthly/klines/{a}/1h/{name}'; path=cache/name
    if not path.exists():
        with urllib.request.urlopen(url,timeout=60) as r: path.write_bytes(r.read())
    payload=path.read_bytes()
    with zipfile.ZipFile(io.BytesIO(payload)) as z: rows=list(csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]))))
    if rows and not rows[0][0].isdigit(): rows=rows[1:]
    out=[]
    for r in rows:
        t=int(r[0]); t=t//1000 if t>10**14 else t; out.append(dict(timestamp=t,open=float(r[1]),high=float(r[2]),low=float(r[3]),close=float(r[4]),quote_volume=float(r[7])))
    return a,out,dict(symbol=a,url=url,sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload),rows=len(out))
def folds(): return [('2022_control',stamp(2022,1),stamp(2023,1))]+[(str(y),stamp(y,1),stamp(y+1,1) if y<2026 else stamp(2026,10)) for y in range(2023,2027)]+[('continuous_oos',stamp(2023,1),stamp(2026,10))]
def aggregate(ts):
    w=sum(max(0,t['pnl']) for t in ts); l=-sum(min(0,t['pnl']) for t in ts); return dict(trades=len(ts),net_pnl=w-l,profit_factor=w/l if l else None,expectancy=(w-l)/len(ts) if ts else None)
def main():
    cache=pathlib.Path(sys.argv[1]); cache.mkdir(parents=True,exist_ok=True); dest=pathlib.Path(sys.argv[2]); dest.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as p: chunks=list(p.map(fetch,[(a,y,m,cache) for a in ASSETS for y,m in MONTHS]))
    grouped={a:[] for a in ASSETS}; manifest=[]
    for a,rows,src in chunks: grouped[a].extend(rows); manifest.append(src)
    raw={a:len(v) for a,v in grouped.items()}; maps={a:{b['timestamp']:b for b in v} for a,v in grouped.items()}; common=sorted(set.intersection(*(set(v) for v in maps.values()))); data={a:[maps[a][t] for t in common] for a in ASSETS}; validate(data)
    quality=dict(raw_rows=raw,aligned_rows=len(common),duplicates={a:raw[a]-len(maps[a]) for a in ASSETS},omitted={a:len(set(maps[a])-set(common)) for a in ASSETS},gaps=[(x,y,(y-x)//STEP-1) for x,y in zip(common,common[1:]) if y-x!=STEP])
    runs={}; ledger={}
    for name,start,end in folds():
        for cost,mult in (('base',1),('stress',2)):
            c=replace(Config(),fee=Config().fee*mult,slippage=Config().slippage*mult); trades=backtest(data,start,end,c); key=f'{name}_{cost}'; runs[key]=score(data['XRPUSDT'],trades,10_000,c); runs[key]['slippage_cost']=sum(t['slippage_cost'] for t in trades); ledger[key]=[dict(t,signal_timestamp=data['XRPUSDT'][t['signal_index']]['timestamp'],entry_timestamp=data['XRPUSDT'][t['entry_index']]['timestamp'],exit_timestamp=data['XRPUSDT'][t['exit_index']]['timestamp']) for t in trades]; print(key,runs[key],flush=True)
    years=[str(y) for y in range(2023,2027)]; bt=[t for y in years for t in ledger[f'{y}_base']]; st=[t for y in years for t in ledger[f'{y}_stress']]; base,stress=aggregate(bt),aggregate(st); by_year={y:runs[f'{y}_base']['net_pnl'] for y in years}; monthly={}
    for t in bt:
        m=dt.datetime.fromtimestamp(t['entry_timestamp']/1000,dt.timezone.utc).strftime('%Y-%m'); monthly[m]=monthly.get(m,0)+t['pnl']
    positive=sum(max(0,v) for v in monthly.values()); gates=dict(sample=base['trades']>=100,base_net=base['net_pnl']>0,base_expectancy=(base['expectancy'] or 0)>0,base_pf=(base['profit_factor'] or 0)>1.15,stress_net=stress['net_pnl']>0,stress_expectancy=(stress['expectancy'] or 0)>0,stress_pf=(stress['profit_factor'] or 0)>1.02,three_positive_years=sum(v>0 for v in by_year.values())>=3,final_year=by_year['2026']>0,drawdown=all(runs[f'continuous_oos_{x}']['max_drawdown_pct']<=10 for x in ('base','stress')),concentration=base['net_pnl']>0 and positive>0 and max(monthly.values(),default=0)<=.40*positive)
    protocol=pathlib.Path('research/attention_share_protocol.md'); result=dict(strategy='XRP_ATTENTION_SHARE_SURGE_V1',status='NEPROSEL' if not all(gates.values()) else 'TEST NEDOKONCEN: forward evidence required',protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),manifest=manifest,data_quality=quality,runs=runs,aggregate_oos=base,aggregate_stress=stress,by_year=by_year,monthly_oos=monthly,gates=gates,limitations=['Cross-market quote volume differs by asset price and turnover structure.','Exploratory history.','Local hashes are not publisher signatures.','No independent forward PAPER evidence.'])
    (dest/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');
    with gzip.open(dest/'trades.json.gz','wt') as h: json.dump(ledger,h)
    print(result['status'],gates)
if __name__=='__main__': main()

