"""Download real Binance spot archives and run the frozen compression screen."""
import concurrent.futures, csv, datetime as dt, gzip, hashlib, io, json, pathlib, sys, urllib.request, zipfile
from dataclasses import replace
from research.volatility_compression_v1 import Config, STEP, backtest, validate
from research.run_autocorr_history import metrics, stamp

MONTHS=[(y,m) for y in range(2022,2027) for m in range(1,13) if (y,m)<(2026,10)]

def fetch(job):
    y,m,cache=job; name=f"XRPUSDT-1h-{y}-{m:02d}.zip"; url=f"https://data.binance.vision/data/spot/monthly/klines/XRPUSDT/1h/{name}"; path=cache/name
    if not path.exists():
        with urllib.request.urlopen(url,timeout=60) as r: path.write_bytes(r.read())
    payload=path.read_bytes()
    with zipfile.ZipFile(io.BytesIO(payload)) as z: rows=list(csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]))))
    if rows and not rows[0][0].isdigit(): rows=rows[1:]
    out=[]
    for r in rows:
        t=int(r[0]); t=t//1000 if t>10**14 else t
        out.append(dict(timestamp=t,open=float(r[1]),high=float(r[2]),low=float(r[3]),close=float(r[4])))
    return out,dict(url=url,sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload),rows=len(out))

def folds():
    return [("2022_control",stamp(2022,1),stamp(2023,1))]+[(str(y),stamp(y,1),stamp(y+1,1) if y<2026 else stamp(2026,10)) for y in range(2023,2027)]+[("continuous_oos",stamp(2023,1),stamp(2026,10))]

def aggregate(trades):
    wins=sum(max(0,t["pnl"]) for t in trades); losses=-sum(min(0,t["pnl"]) for t in trades); net=wins-losses
    return dict(trades=len(trades),net_pnl=net,profit_factor=wins/losses if losses else None,expectancy=net/len(trades) if trades else None)

def main():
    cache=pathlib.Path(sys.argv[1]); cache.mkdir(parents=True,exist_ok=True); dest=pathlib.Path(sys.argv[2]); dest.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool: chunks=list(pool.map(fetch,[(y,m,cache) for y,m in MONTHS]))
    raw=[b for rows,_ in chunks for b in rows]; by_time={b["timestamp"]:b for b in raw}; bars=[by_time[t] for t in sorted(by_time)]; validate(bars)
    quality=dict(raw_rows=len(raw),unique_rows=len(bars),duplicates=len(raw)-len(bars),gaps=[dict(after=a["timestamp"],before=b["timestamp"],missing_hours=(b["timestamp"]-a["timestamp"])//STEP-1) for a,b in zip(bars,bars[1:]) if b["timestamp"]-a["timestamp"]!=STEP])
    runs={}; ledger={}
    for name,start,end in folds():
        for label,mult in (("base",1),("stress",2)):
            c=replace(Config(),fee=Config().fee*mult,slippage=Config().slippage*mult); trades=backtest(bars,start,end,c); key=f"{name}_{label}"
            runs[key]=metrics(bars,trades,10_000,c); runs[key]["slippage_cost"]=sum(t["slippage_cost"] for t in trades)
            ledger[key]=[dict(t,signal_timestamp=bars[t["signal_index"]]["timestamp"],entry_timestamp=bars[t["entry_index"]]["timestamp"],exit_timestamp=bars[t["exit_index"]]["timestamp"]) for t in trades]
            print(key,runs[key],flush=True)
    years=[str(y) for y in range(2023,2027)]; base_trades=[t for y in years for t in ledger[f"{y}_base"]]; stress_trades=[t for y in years for t in ledger[f"{y}_stress"]]; base=aggregate(base_trades); stress=aggregate(stress_trades)
    by_year={y:runs[f"{y}_base"]["net_pnl"] for y in years}; stress_by_year={y:runs[f"{y}_stress"]["net_pnl"] for y in years}; monthly={}
    for t in base_trades:
        month=dt.datetime.fromtimestamp(t["entry_timestamp"]/1000,dt.timezone.utc).strftime("%Y-%m"); monthly[month]=monthly.get(month,0)+t["pnl"]
    positive=sum(max(0,x) for x in monthly.values())
    gates=dict(sample=base["trades"]>=100,base_net=base["net_pnl"]>0,base_expectancy=(base["expectancy"] or 0)>0,base_pf=(base["profit_factor"] or 0)>1.15,stress_net=stress["net_pnl"]>0,stress_expectancy=(stress["expectancy"] or 0)>0,stress_pf=(stress["profit_factor"] or 0)>1.02,three_positive_years=sum(x>0 for x in by_year.values())>=3,final_year=by_year["2026"]>0,three_positive_stress_years=sum(x>0 for x in stress_by_year.values())>=3,drawdown=max(runs["continuous_oos_base"]["max_drawdown_pct"],runs["continuous_oos_stress"]["max_drawdown_pct"])<=10,concentration=base["net_pnl"]>0 and positive>0 and max(monthly.values(),default=0)<=.40*positive)
    protocol=pathlib.Path("research/volatility_compression_protocol.md")
    result=dict(strategy="XRP_VOLATILITY_COMPRESSION_BREAKOUT_V1",status="NEPROSEL" if not all(gates.values()) else "TEST NEDOKONCEN: independent forward PAPER evidence required",protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),manifest=[src for _,src in chunks],data_quality=quality,runs=runs,aggregate_oos=base,aggregate_stress=stress,by_year=by_year,stress_by_year=stress_by_year,monthly_oos=monthly,gates=gates,limitations=["Exploratory history; previously inspected dates are not untouched.","Local SHA256 fingerprints are not publisher signatures.","OHLC ordering is unknown; ambiguous stop/target bars use the stop.","Conservative drawdown marks the entire exit candle low.","No independent forward PAPER evidence exists."])
    (dest/"results.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    with gzip.open(dest/"trades.json.gz","wt") as h: json.dump(ledger,h)
    print(result["status"],gates,flush=True)

if __name__=="__main__": main()

