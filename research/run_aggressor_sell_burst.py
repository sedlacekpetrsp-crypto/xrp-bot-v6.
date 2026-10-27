"""Stream Binance aggTrades, derive minute bars, and run frozen validation."""
import concurrent.futures,csv,datetime as dt,gzip,hashlib,io,json,os,pathlib,shutil,subprocess,sys,urllib.request,zipfile
from dataclasses import replace
from research.aggressor_sell_burst_v1 import Config,MinuteBuilder,STEP,TS,O,H,L,C,VALID,backtest,validate
from research.run_autocorr_history import stamp

MONTHS=[(y,m) for y in range(2022,2027) for m in range(1,13) if (y,m)<(2026,10)]
REORDER_SHA='cab6508d0123cee29a576af84794f1328e0093996cb93a56e7036e7c22ec9e9b'

def download(job):
    y,m,cache=job; name=f'XRPUSDT-aggTrades-{y}-{m:02d}.zip'; url=f'https://data.binance.vision/data/spot/monthly/aggTrades/XRPUSDT/{name}'; path=cache/name
    if not path.exists():
        with urllib.request.urlopen(url,timeout=120) as r: path.write_bytes(r.read())
    h=hashlib.sha256(); size=0
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk); size+=len(chunk)
    return path,dict(url=url,sha256=h.hexdigest(),bytes=size)

def iter_rows(path,src):
    if src['sha256']==REORDER_SHA:
        raw=path.with_suffix('.raw.csv'); ordered=path.with_suffix('.ordered.csv')
        if not ordered.exists():
            with zipfile.ZipFile(path) as z:
                names=z.namelist()
                if len(names)!=1: raise ValueError('archive members')
                with z.open(names[0]) as inp, raw.open('wb') as out: shutil.copyfileobj(inp,out,1024*1024)
            env=dict(os.environ,LC_ALL='C'); subprocess.run(['sort','-t,','-k1,1n',str(raw),'-o',str(ordered)],check=True,env=env)
            raw.unlink()
        src.update(reordered=True,raw_nonmonotonic_boundaries=2)
        with ordered.open() as handle:
            yield from csv.reader(handle)
    else:
        src.update(reordered=False,raw_nonmonotonic_boundaries=0)
        with zipfile.ZipFile(path) as z:
            names=z.namelist()
            if len(names)!=1: raise ValueError('archive members')
            with io.TextIOWrapper(z.open(names[0])) as handle:
                yield from csv.reader(handle)

def folds(): return [('2022_control',stamp(2022,1),stamp(2023,1))]+[(str(y),stamp(y,1),stamp(y+1,1) if y<2026 else stamp(2026,10)) for y in range(2023,2027)]+[('continuous_oos',stamp(2023,1),stamp(2026,10))]

def score(bars,trades,initial,c):
    wins=sum(max(0,t['pnl']) for t in trades); losses=-sum(min(0,t['pnl']) for t in trades); cash=initial; peak=initial; dd=0.; active=None; byentry={t['entry_index']:t for t in trades}; monthly={}
    for i,b in enumerate(bars):
        if i in byentry: active=byentry[i]
        marked=cash
        if active:
            mark=b[L]*(1-c.slippage); marked=cash+active['qty']*(mark-active['entry'])-c.fee*active['qty']*(active['entry']+mark)
            if i==active['exit_index']: cash+=active['pnl']; active=None; marked=cash
        dd=max(dd,(peak-marked)/peak); peak=max(peak,cash)
    for t in trades:
        month=dt.datetime.fromtimestamp(bars[t['exit_index']][TS]/1000,dt.timezone.utc).strftime('%Y-%m'); monthly[month]=monthly.get(month,0)+t['pnl']
    net=wins-losses
    return dict(trades=len(trades),net_pnl=net,return_pct=net/initial*100,profit_factor=wins/losses if losses else None,expectancy=net/len(trades) if trades else None,max_drawdown_pct=dd*100,monthly_net=monthly,fees=sum(t['fees'] for t in trades),slippage_cost=sum(t['slippage_cost'] for t in trades))

def aggregate(trades):
    w=sum(max(0,t['pnl']) for t in trades); l=-sum(min(0,t['pnl']) for t in trades); n=w-l
    return dict(trades=len(trades),net_pnl=n,profit_factor=w/l if l else None,expectancy=n/len(trades) if trades else None)

def main():
    cache=pathlib.Path(sys.argv[1]); cache.mkdir(parents=True,exist_ok=True); dest=pathlib.Path(sys.argv[2]); dest.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as p: archives=list(p.map(download,[(y,m,cache) for y,m in MONTHS]))
    builder=MinuteBuilder(); manifest=[]
    for index,(path,src) in enumerate(archives):
        records=0; exact_duplicates=0; first_id=last_id=first_time=last_time=None; previous_row=None
        for row in iter_rows(path,src):
            if not row or not row[0].isdigit(): continue
            if src['reordered'] and previous_row is not None and row[0]==previous_row[0]:
                if row!=previous_row: raise ValueError('conflicting duplicate aggregate trade')
                exact_duplicates+=1; continue
            previous_row=row
            trade_id=int(row[0]); ts=int(row[5]); ts=ts//1000 if ts>10**14 else ts; price=float(row[1]); seller=row[6].lower()=='true'
            builder.feed(trade_id,ts,price,seller); records+=1
            if first_id is None: first_id,first_time=trade_id,ts
            last_id,last_time=trade_id,ts
        src.update(records=records,exact_duplicates_removed=exact_duplicates,first_id=first_id,last_id=last_id,first_timestamp=first_time,last_timestamp=last_time); manifest.append(src); print(f'parsed {index+1}/{len(archives)} {path.name} records={records} exact_duplicates={exact_duplicates}',flush=True)
    bars=builder.finish(); validate(bars)
    quality=dict(records=builder.records,minute_bars=len(bars),id_discontinuities=builder.id_gaps,invalid_minutes=sum(not b[VALID] for b in bars),reordered_archives=sum(x['reordered'] for x in manifest),raw_nonmonotonic_boundaries=sum(x['raw_nonmonotonic_boundaries'] for x in manifest),exact_duplicate_rows_removed=sum(x['exact_duplicates_removed'] for x in manifest),calendar_gaps=[dict(after=a[TS],before=b[TS],missing_minutes=(b[TS]-a[TS])//STEP-1) for a,b in zip(bars,bars[1:]) if b[TS]-a[TS]!=STEP])
    runs={}; ledger={}
    for name,start,end in folds():
        for label,mult in (('base',1),('stress',2)):
            c=replace(Config(),fee=Config().fee*mult,slippage=Config().slippage*mult); trades=backtest(bars,start,end,c); key=f'{name}_{label}'; runs[key]=score(bars,trades,10_000,c); ledger[key]=[dict(t,signal_timestamp=bars[t['signal_index']][TS],entry_timestamp=bars[t['entry_index']][TS],exit_timestamp=bars[t['exit_index']][TS]) for t in trades]; print(key,runs[key],flush=True)
    years=[str(y) for y in range(2023,2027)]; bt=[t for y in years for t in ledger[f'{y}_base']]; st=[t for y in years for t in ledger[f'{y}_stress']]; base,stress=aggregate(bt),aggregate(st); by_year={y:runs[f'{y}_base']['net_pnl'] for y in years}; stress_by_year={y:runs[f'{y}_stress']['net_pnl'] for y in years}; monthly={}
    for t in bt:
        m=dt.datetime.fromtimestamp(t['entry_timestamp']/1000,dt.timezone.utc).strftime('%Y-%m'); monthly[m]=monthly.get(m,0)+t['pnl']
    positive=sum(max(0,v) for v in monthly.values()); gates=dict(sample=base['trades']>=250,base_net=base['net_pnl']>0,base_expectancy=(base['expectancy'] or 0)>0,base_pf=(base['profit_factor'] or 0)>1.15,stress_net=stress['net_pnl']>0,stress_expectancy=(stress['expectancy'] or 0)>0,stress_pf=(stress['profit_factor'] or 0)>1.02,three_positive_years=sum(v>0 for v in by_year.values())>=3,final_year=by_year['2026']>0,three_positive_stress_years=sum(v>0 for v in stress_by_year.values())>=3,drawdown=max(runs['continuous_oos_base']['max_drawdown_pct'],runs['continuous_oos_stress']['max_drawdown_pct'])<=10,concentration=base['net_pnl']>0 and positive>0 and max(monthly.values(),default=0)<=.25*positive)
    protocol=pathlib.Path('research/aggressor_sell_burst_protocol.md'); result=dict(strategy='XRP_AGGRESSOR_SELL_BURST_REVERSAL_V1',status='NEPROSEL' if not all(gates.values()) else 'TEST NEDOKONCEN: independent forward PAPER evidence required',protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),manifest=manifest,data_quality=quality,runs=runs,aggregate_oos=base,aggregate_stress=stress,by_year=by_year,stress_by_year=stress_by_year,monthly_oos=monthly,gates=gates,limitations=['Aggregate-trade events can combine multiple fills and are not individual order messages.','Execution uses first trade and OHLC trade extrema plus frozen slippage, not historical bid/ask queue position.','Exploratory history; local SHA256 are not publisher signatures.','No independent forward PAPER evidence.'])
    (dest/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');
    with gzip.open(dest/'trades.json.gz','wt') as h: json.dump(ledger,h)
    print(result['status'],gates,flush=True)
if __name__=='__main__': main()

