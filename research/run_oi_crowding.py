"""Download Binance futures metrics and spot bars; run frozen OOS screen."""
import concurrent.futures,csv,gzip,hashlib,io,json,pathlib,sys,urllib.request,zipfile
from datetime import datetime,timedelta,timezone
from dataclasses import replace
from research.oi_crowding_v1 import Config,backtest,validate
from research.run_autocorr_history import metrics as score,stamp
def days():
    d=datetime(2024,1,1,tzinfo=timezone.utc);end=datetime(2026,10,1,tzinfo=timezone.utc)
    while d<end:yield d;d+=timedelta(days=1)
def get(url,path):
    if not path.exists():
        with urllib.request.urlopen(url,timeout=45) as r:path.write_bytes(r.read())
    return path.read_bytes()
def fetch_metric(job):
    d,cache=job;ds=d.strftime('%Y-%m-%d');name=f'XRPUSDT-metrics-{ds}.zip';url=f'https://data.binance.vision/data/futures/um/daily/metrics/XRPUSDT/{name}';payload=get(url,cache/name)
    with zipfile.ZipFile(io.BytesIO(payload)) as z:rows=list(csv.DictReader(io.TextIOWrapper(z.open(name[:-4]+'.csv'))))
    out=[]
    for r in rows:
        t=int(datetime.strptime(r['create_time'],'%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp()*1000);out.append(dict(timestamp=t,open_interest=float(r['sum_open_interest']),long_short=float(r['count_long_short_ratio']),taker_ratio=float(r['sum_taker_long_short_vol_ratio'])))
    out.sort(key=lambda x:x['timestamp']);return out,dict(url=url,sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload),rows=len(out))
def fetch_spot(job):
    y,m,cache=job;name=f'XRPUSDT-5m-{y}-{m:02d}.zip';url=f'https://data.binance.vision/data/spot/monthly/klines/XRPUSDT/5m/{name}';payload=get(url,cache/name)
    with zipfile.ZipFile(io.BytesIO(payload)) as z:rows=list(csv.reader(io.TextIOWrapper(z.open(name[:-4]+'.csv'))))
    out=[]
    for r in rows:
        t=int(r[0]);t=t//1000 if t>10**14 else t;out.append(dict(timestamp=t,open=float(r[1]),high=float(r[2]),low=float(r[3]),close=float(r[4])))
    return out,dict(url=url,sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload),rows=len(out))
def agg(ts):
    w=sum(max(0,t['pnl']) for t in ts);l=-sum(min(0,t['pnl']) for t in ts);return dict(trades=len(ts),net_pnl=w-l,profit_factor=w/l if l else None,expectancy=(w-l)/len(ts) if ts else None)
def main():
    cache=pathlib.Path(sys.argv[1]);cache.mkdir(parents=True,exist_ok=True);dest=pathlib.Path(sys.argv[2]);dest.mkdir(parents=True,exist_ok=True);manifest=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=32) as p:mc=list(p.map(fetch_metric,[(d,cache) for d in days()]))
    months=[(y,m) for y in range(2024,2027) for m in range(1,13) if (y,m)<(2026,10)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as p:sc=list(p.map(fetch_spot,[(y,m,cache) for y,m in months]))
    rawm=[x for chunk,_ in mc for x in chunk];rawb=[x for chunk,_ in sc for x in chunk];manifest=[src for _,src in mc+sc]
    md={x['timestamp']:x for x in rawm};bd={x['timestamp']:x for x in rawb};common=sorted(set(md)&set(bd));m=[md[t] for t in common];bars=[bd[t] for t in common];validate(bars,m)
    omitted=dict(metric_only=sorted(set(md)-set(bd)),spot_only=sorted(set(bd)-set(md)),metric_duplicates=len(rawm)-len(md));runs={};ledger={}
    folds=[('2024_control',stamp(2024,1),stamp(2025,1)),('2025Q1',stamp(2025,1),stamp(2025,4)),('2025Q2',stamp(2025,4),stamp(2025,7)),('2025Q3',stamp(2025,7),stamp(2025,10)),('2025Q4',stamp(2025,10),stamp(2026,1)),('2026Q1',stamp(2026,1),stamp(2026,4)),('2026Q2',stamp(2026,4),stamp(2026,7)),('2026Q3',stamp(2026,7),stamp(2026,10)),('continuous_oos',stamp(2025,1),stamp(2026,10))]
    for name,start,end in folds:
      for cost,mult in [('base',1),('stress',2)]:
        c=replace(Config(),fee=.00095*mult,slippage=.0002*mult);ts=backtest(bars,m,start,end,c);key=f'{name}_{cost}';runs[key]=score(bars,ts,10000,c);runs[key]['slippage_cost']=sum(t['slippage_cost'] for t in ts);ledger[key]=[dict(t,entry_timestamp=bars[t['entry_index']]['timestamp'],exit_timestamp=bars[t['exit_index']]['timestamp']) for t in ts];print(key,runs[key],flush=True)
    qs=('2025Q1','2025Q2','2025Q3','2025Q4','2026Q1','2026Q2','2026Q3');base=[t for q in qs for t in ledger[f'{q}_base']];stress=[t for q in qs for t in ledger[f'{q}_stress']];a,b=agg(base),agg(stress);quarter={q:runs[f'{q}_base']['net_pnl'] for q in qs}
    gates=dict(sample=a['trades']>=150,base_net=a['net_pnl']>0,base_expectancy=(a['expectancy'] or 0)>0,base_pf=(a['profit_factor'] or 0)>1.15,stress_net=b['net_pnl']>0,stress_expectancy=(b['expectancy'] or 0)>0,stress_pf=(b['profit_factor'] or 0)>1.02,five_positive_quarters=sum(v>0 for v in quarter.values())>=5,final_quarter=quarter['2026Q3']>0,drawdown=all(runs[f'continuous_oos_{x}']['max_drawdown_pct']<=10 for x in ('base','stress')),concentration=a['net_pnl']>0 and max(quarter.values())<=.4*a['net_pnl'])
    p=pathlib.Path('research/oi_crowding_protocol.md');result=dict(strategy='XRP_OI_CROWDING_UNWIND_V1',status='NEPROSEL' if not all(gates.values()) else 'TEST NEDOKONCEN: forward evidence required',protocol=str(p),protocol_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),manifest=manifest,alignment=omitted,runs=runs,aggregate_oos=a,aggregate_stress=b,by_quarter=quarter,gates=gates,limitations=['Exploratory history.','Local SHA256 are not publisher signatures.','Metrics snapshots aligned to same timestamp; next-bar execution.','No forward PAPER evidence.'])
    (dest/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');
    with gzip.open(dest/'trades.json.gz','wt') as f:json.dump(ledger,f)
    print(result['status'],gates)
if __name__=='__main__':main()
