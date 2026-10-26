"""Download Binance book-depth/spot archives and run the frozen screen."""
import concurrent.futures,csv,datetime as dt,gzip,hashlib,io,json,pathlib,sys,urllib.error,urllib.request,zipfile
from dataclasses import replace
from research.orderbook_depth_v1 import Config,STEP,backtest,validate
from research.run_autocorr_history import metrics as score,stamp

START=dt.date(2024,1,1); END=dt.date(2026,10,1)
DATES=[]; day=START
while day<END: DATES.append(day); day+=dt.timedelta(days=1)
MONTHS=[(y,m) for y in range(2024,2027) for m in range(1,13) if (y,m)<(2026,10)]

def get(url,path):
    if not path.exists():
        with urllib.request.urlopen(url,timeout=90) as response: path.write_bytes(response.read())
    return path.read_bytes()

def depth_fetch(job):
    day,cache=job; ds=day.isoformat(); name=f'XRPUSDT-bookDepth-{ds}.zip'; url=f'https://data.binance.vision/data/futures/um/daily/bookDepth/XRPUSDT/{name}'; points={}
    try: payload=get(url,cache/name)
    except urllib.error.HTTPError as error:
        if error.code==404: return [],dict(kind='bookDepth',url=url,missing_http_404=True,rows=0)
        raise
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        rows=csv.DictReader(io.TextIOWrapper(archive.open(archive.namelist()[0])))
        for row in rows:
            if row['timestamp'][14:19]!='59:30' or row['percentage'] not in ('-1','1'): continue
            when=dt.datetime.strptime(row['timestamp'],'%Y-%m-%d %H:%M:%S').replace(tzinfo=dt.timezone.utc)
            hour=int(when.replace(minute=0,second=0).timestamp()*1000); slot=points.setdefault(hour,{})
            slot['bid_notional' if row['percentage']=='-1' else 'ask_notional']=float(row['notional'])
    out=[dict(timestamp=t,**v) for t,v in points.items() if set(v)=={'bid_notional','ask_notional'}]
    return out,dict(kind='bookDepth',url=url,sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload),rows=len(out))

def spot_fetch(job):
    y,m,cache=job; name=f'XRPUSDT-1h-{y}-{m:02d}.zip'; url=f'https://data.binance.vision/data/spot/monthly/klines/XRPUSDT/1h/{name}'; payload=get(url,cache/f'spot-{name}')
    with zipfile.ZipFile(io.BytesIO(payload)) as archive: rows=list(csv.reader(io.TextIOWrapper(archive.open(archive.namelist()[0]))))
    if rows and not rows[0][0].isdigit(): rows=rows[1:]
    out=[]
    for row in rows:
        t=int(row[0]); t=t//1000 if t>10**14 else t; out.append(dict(timestamp=t,open=float(row[1]),high=float(row[2]),low=float(row[3]),close=float(row[4])))
    return out,dict(kind='spot',url=url,sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload),rows=len(out))

def folds():
    out=[('2024_control',stamp(2024,1),stamp(2025,1))]
    for y in (2025,2026):
        for q,m in enumerate((1,4,7,10),1):
            if (y,m)>=(2026,10): continue
            ey,em=(y+1,1) if m==10 else (y,m+3); out.append((f'{y}Q{q}',stamp(y,m),stamp(ey,em)))
    out.append(('continuous_oos',stamp(2025,1),stamp(2026,10))); return out

def aggregate(ts):
    w=sum(max(0,t['pnl']) for t in ts); l=-sum(min(0,t['pnl']) for t in ts)
    return dict(trades=len(ts),net_pnl=w-l,profit_factor=w/l if l else None,expectancy=(w-l)/len(ts) if ts else None)

def main():
    cache=pathlib.Path(sys.argv[1]); cache.mkdir(parents=True,exist_ok=True); dest=pathlib.Path(sys.argv[2]); dest.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=32) as p: chunks=list(p.map(depth_fetch,[(d,cache) for d in DATES]))
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as p: spots=list(p.map(spot_fetch,[(y,m,cache) for y,m in MONTHS]))
    depth_raw=[]; spot_raw=[]; manifest=[]
    for rows,src in chunks: depth_raw.extend(rows); manifest.append(src)
    for rows,src in spots: spot_raw.extend(rows); manifest.append(src)
    dm={r['timestamp']:r for r in depth_raw}; sm={r['timestamp']:r for r in spot_raw}; common=sorted(set(dm)&set(sm)); bars=[sm[t] for t in common]; depth=[dm[t] for t in common]; validate(bars,depth)
    quality=dict(depth_rows=len(depth_raw),spot_rows=len(spot_raw),aligned_rows=len(common),depth_duplicates=len(depth_raw)-len(dm),spot_duplicates=len(spot_raw)-len(sm),depth_only=len(set(dm)-set(sm)),spot_only=len(set(sm)-set(dm)),gaps=[(a,b,(b-a)//STEP-1) for a,b in zip(common,common[1:]) if b-a!=STEP])
    runs={}; ledger={}
    for name,start,end in folds():
        for cost,mult in (('base',1),('stress',2)):
            c=replace(Config(),fee=Config().fee*mult,slippage=Config().slippage*mult); trades=backtest(bars,depth,start,end,c); key=f'{name}_{cost}'; runs[key]=score(bars,trades,10_000,c); runs[key]['slippage_cost']=sum(t['slippage_cost'] for t in trades)
            ledger[key]=[dict(t,signal_timestamp=bars[t['signal_index']]['timestamp'],entry_timestamp=bars[t['entry_index']]['timestamp'],exit_timestamp=bars[t['exit_index']]['timestamp']) for t in trades]; print(key,runs[key],flush=True)
    qs=[n for n,_,_ in folds() if n not in ('2024_control','continuous_oos')]; bt=[t for q in qs for t in ledger[f'{q}_base']]; st=[t for q in qs for t in ledger[f'{q}_stress']]; base,stress=aggregate(bt),aggregate(st); byq={q:runs[f'{q}_base']['net_pnl'] for q in qs}; positive=sum(max(0,v) for v in byq.values())
    gates=dict(sample=base['trades']>=150,base_net=base['net_pnl']>0,base_expectancy=(base['expectancy'] or 0)>0,base_pf=(base['profit_factor'] or 0)>1.15,stress_net=stress['net_pnl']>0,stress_expectancy=(stress['expectancy'] or 0)>0,stress_pf=(stress['profit_factor'] or 0)>1.02,five_positive_quarters=sum(v>0 for v in byq.values())>=5,final_quarter=byq['2026Q3']>0,drawdown=all(runs[f'continuous_oos_{x}']['max_drawdown_pct']<=10 for x in ('base','stress')),concentration=base['net_pnl']>0 and positive>0 and max(byq.values())<=.35*positive)
    protocol=pathlib.Path('research/orderbook_depth_protocol.md'); result=dict(strategy='XRP_ORDERBOOK_DEPTH_IMBALANCE_V1',status='NEPROSEL' if not all(gates.values()) else 'TEST NEDOKONCEN: forward evidence required',protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),manifest=manifest,data_quality=quality,runs=runs,aggregate_oos=base,aggregate_stress=stress,by_quarter=byq,gates=gates,limitations=['Futures passive depth signals spot execution.','Resting depth can be cancelled or spoofed.','Local hashes are not publisher signatures.','No independent forward PAPER evidence.'])
    (dest/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');
    with gzip.open(dest/'trades.json.gz','wt') as h: json.dump(ledger,h)
    print(result['status'],gates)

if __name__=='__main__': main()

