"""Download Binance premium-index and spot bars; run frozen OOS screen."""
import concurrent.futures,csv,gzip,hashlib,io,json,pathlib,sys,urllib.request,zipfile
from dataclasses import replace
from research.premium_recovery_v1 import Config,STEP,backtest,validate
from research.run_autocorr_history import metrics as score,stamp

MONTHS=[(y,m) for y in range(2022,2027) for m in range(1,13) if (y,m)<(2026,10)]


def get(url,path):
    if not path.exists():
        with urllib.request.urlopen(url,timeout=45) as response: path.write_bytes(response.read())
    return path.read_bytes()


def fetch(job):
    kind,y,m,cache=job; name=f'XRPUSDT-1h-{y}-{m:02d}.zip'
    if kind=='premium': url=f'https://data.binance.vision/data/futures/um/monthly/premiumIndexKlines/XRPUSDT/1h/{name}'
    else: url=f'https://data.binance.vision/data/spot/monthly/klines/XRPUSDT/1h/{name}'
    payload=get(url,cache/f'{kind}-{name}')
    with zipfile.ZipFile(io.BytesIO(payload)) as archive: rows=list(csv.reader(io.TextIOWrapper(archive.open(archive.namelist()[0]))))
    if rows and not rows[0][0].isdigit(): rows=rows[1:]
    output=[]
    for row in rows:
        timestamp=int(row[0]); timestamp=timestamp//1000 if timestamp>10**14 else timestamp
        output.append(dict(timestamp=timestamp,open=float(row[1]),high=float(row[2]),low=float(row[3]),close=float(row[4])))
    return kind,output,dict(kind=kind,url=url,sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload),rows=len(output))


def folds():
    result=[('2022_control',stamp(2022,1),stamp(2023,1))]
    for year in range(2023,2027):
        for quarter,month in enumerate((1,4,7,10),1):
            if (year,month)>=(2026,10): continue
            ey,em=(year+1,1) if month==10 else (year,month+3)
            result.append((f'{year}Q{quarter}',stamp(year,month),stamp(ey,em)))
    result.append(('continuous_oos',stamp(2023,1),stamp(2026,10))); return result


def aggregate(trades):
    wins=sum(max(0,t['pnl']) for t in trades); losses=-sum(min(0,t['pnl']) for t in trades)
    return dict(trades=len(trades),net_pnl=wins-losses,profit_factor=wins/losses if losses else None,expectancy=(wins-losses)/len(trades) if trades else None)


def main():
    cache=pathlib.Path(sys.argv[1]); cache.mkdir(parents=True,exist_ok=True); destination=pathlib.Path(sys.argv[2]); destination.mkdir(parents=True,exist_ok=True)
    jobs=[(kind,y,m,cache) for kind in ('premium','spot') for y,m in MONTHS]
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool: chunks=list(pool.map(fetch,jobs))
    grouped={'premium':[],'spot':[]}; manifest=[]
    for kind,rows,source in chunks: grouped[kind].extend(rows); manifest.append(source)
    raw={kind:len(rows) for kind,rows in grouped.items()}; maps={kind:{row['timestamp']:row for row in rows} for kind,rows in grouped.items()}
    common=sorted(set(maps['premium'])&set(maps['spot'])); premium=[maps['premium'][t] for t in common]; bars=[maps['spot'][t] for t in common]; validate(bars,premium)
    quality=dict(premium_duplicates=raw['premium']-len(maps['premium']),spot_duplicates=raw['spot']-len(maps['spot']),premium_only=sorted(set(maps['premium'])-set(maps['spot'])),spot_only=sorted(set(maps['spot'])-set(maps['premium'])),aligned_gaps=[(a,b,(b-a)//STEP-1) for a,b in zip(common,common[1:]) if b-a!=STEP])
    runs={}; ledger={}
    for name,start,end in folds():
        for cost,multiplier in (('base',1),('stress',2)):
            config=replace(Config(),fee=Config().fee*multiplier,slippage=Config().slippage*multiplier); trades=backtest(bars,premium,start,end,config); key=f'{name}_{cost}'
            runs[key]=score(bars,trades,10_000,config); runs[key]['slippage_cost']=sum(t['slippage_cost'] for t in trades)
            ledger[key]=[dict(t,signal_timestamp=bars[t['signal_index']]['timestamp'],entry_timestamp=bars[t['entry_index']]['timestamp'],exit_timestamp=bars[t['exit_index']]['timestamp']) for t in trades]
            print(key,runs[key],flush=True)
    quarters=[name for name,_,_ in folds() if name not in ('2022_control','continuous_oos')]; base_trades=[t for q in quarters for t in ledger[f'{q}_base']]; stress_trades=[t for q in quarters for t in ledger[f'{q}_stress']]
    base,stress=aggregate(base_trades),aggregate(stress_trades); by_quarter={q:runs[f'{q}_base']['net_pnl'] for q in quarters}; positive_total=sum(max(0,value) for value in by_quarter.values())
    gates=dict(sample=base['trades']>=150,base_net=base['net_pnl']>0,base_expectancy=(base['expectancy'] or 0)>0,base_pf=(base['profit_factor'] or 0)>1.15,stress_net=stress['net_pnl']>0,stress_expectancy=(stress['expectancy'] or 0)>0,stress_pf=(stress['profit_factor'] or 0)>1.02,ten_positive_quarters=sum(value>0 for value in by_quarter.values())>=10,final_quarter=by_quarter['2026Q3']>0,drawdown=all(runs[f'continuous_oos_{cost}']['max_drawdown_pct']<=10 for cost in ('base','stress')),concentration=base['net_pnl']>0 and positive_total>0 and max(by_quarter.values())<=.30*positive_total)
    protocol=pathlib.Path('research/premium_recovery_protocol.md'); result=dict(strategy='XRP_CONTINUOUS_PREMIUM_RECOVERY_V1',status='NEPROSEL' if not all(gates.values()) else 'TEST NEDOKONCEN: forward evidence required',protocol=str(protocol),protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),manifest=manifest,data_quality=quality,runs=runs,aggregate_oos=base,aggregate_stress=stress,by_quarter=by_quarter,gates=gates,limitations=['Exploratory historical evidence.','Local SHA256 are not publisher signatures.','Premium is a signal only; spot trades claim no funding cashflow.','No independent forward PAPER evidence.'])
    (destination/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    with gzip.open(destination/'trades.json.gz','wt') as handle: json.dump(ledger,handle)
    print(result['status'],gates)


if __name__=='__main__': main()
