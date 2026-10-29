"""Download and validate DEFI_YIELD_ROTATION_XRP_V1 on frozen real sources."""
import bisect, csv, datetime as dt, gzip, hashlib, io, json, pathlib, sys, urllib.request, zipfile
from dataclasses import replace
from research.defi_yield_rotation_v1 import Config, DAY, backtest, make_yield_signals, validate_prices

UTC = dt.timezone.utc
MONTHS = [(y,m) for y in range(2023,2027) for m in range(1,13) if (y,m)<(2026,10)]
POOL = "aa70268e-4b52-42bf-a116-608b370f9501"

def get(url,path):
    if not path.exists():
        with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"xrp-research/1.0"}),timeout=120) as r:
            path.write_bytes(r.read())
    return path.read_bytes()

def stamp(y,m=1):
    return int(dt.datetime(y,m,1,tzinfo=UTC).timestamp()*1000)

def yield_history(cache):
    url=f"https://yields.llama.fi/chart/{POOL}"
    payload=get(url,cache/"defillama-aave-v3-ethereum-usdc.json")
    raw=json.loads(payload)["data"]
    rows=[]
    for x in raw:
        ts=int(dt.datetime.fromisoformat(x["timestamp"].replace("Z","+00:00")).timestamp()*1000)
        rows.append(dict(timestamp=ts,apy=float(x["apy"])))
    return rows,dict(kind="defillama_yields",url=url,pool=POOL,sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload),rows=len(raw))

def prices(cache):
    out,manifest=[],[]
    for y,m in MONTHS:
        name=f"XRPUSDT-1d-{y}-{m:02d}.zip"
        url=f"https://data.binance.vision/data/spot/monthly/klines/XRPUSDT/1d/{name}"
        payload=get(url,cache/name)
        with zipfile.ZipFile(io.BytesIO(payload)) as z:
            raw=list(csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]))))
        rows=[]
        for x in raw:
            if x[0].lower().startswith("open"): continue
            ts=int(x[0]); ts=ts//1000 if ts>10**14 else ts
            rows.append(dict(timestamp=ts,open=float(x[1]),high=float(x[2]),low=float(x[3]),close=float(x[4])))
        out += rows
        manifest.append(dict(kind="binance_XRPUSDT_1d",url=url,sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload),rows=len(rows)))
    return out,manifest

def unique(rows,name):
    data={}; duplicates=0
    for x in rows:
        if x["timestamp"] in data:
            if data[x["timestamp"]] != x: raise ValueError("conflicting duplicate "+name)
            duplicates += 1
        data[x["timestamp"]]=x
    return [data[t] for t in sorted(data)],duplicates

def metrics(trades,curve,initial=10000):
    gains=sum(max(0,x["pnl"]) for x in trades); losses=-sum(min(0,x["pnl"]) for x in trades)
    net=sum(x["pnl"] for x in trades); peak=initial; dd=0
    for x in curve:
        peak=max(peak,x["equity"]); dd=max(dd,(peak-x["equity"])/peak*100)
    return dict(trades=len(trades),net_pnl=net,net_return_pct=net/initial*100,
        profit_factor=gains/losses if losses else None,expectancy=net/len(trades) if trades else None,
        max_drawdown_pct=dd,fees=sum(x["fees"] for x in trades),slippage_cost=sum(x["slippage_cost"] for x in trades))

def main():
    cache=pathlib.Path(sys.argv[1]); cache.mkdir(parents=True,exist_ok=True)
    dest=pathlib.Path(sys.argv[2]); dest.mkdir(parents=True,exist_ok=True)
    yr,ym=yield_history(cache); pr,pm=prices(cache)
    yields,ydup=unique(yr,"yield"); rows,pdup=unique(pr,"price"); validate_prices(rows)
    signals=make_yield_signals(yields); price_times=[x["timestamp"] for x in rows]
    mapped={}; after_prices=0
    for s in signals:
        k=bisect.bisect_right(price_times,s["source_timestamp"])
        if k==len(rows): after_prices += 1; continue
        mapped[price_times[k]]=s
    for x in rows:
        if x["timestamp"] in mapped: x["yield_signal"]=mapped[x["timestamp"]]
    gaps=[dict(after=a["timestamp"],before=b["timestamp"],missing_days=(b["timestamp"]-a["timestamp"])//DAY-1) for a,b in zip(rows,rows[1:]) if b["timestamp"]-a["timestamp"]!=DAY]
    folds=[("2023_source_control",stamp(2023),stamp(2024)),("2024",stamp(2024),stamp(2025)),("2025",stamp(2025),stamp(2026)),("2026",stamp(2026),stamp(2026,10)),("continuous_oos",stamp(2024),stamp(2026,10))]
    runs,ledgers={},{}
    for name,start,end in folds:
        for label,multiple in (("base",1),("stress",2)):
            c=Config(); c=replace(c,fee=c.fee*multiple,slippage=c.slippage*multiple)
            trades,curve=backtest(rows,start,end,c)
            key=f"{name}_{label}"; ledgers[key]=trades; runs[key]=metrics(trades,curve)
            print(key,runs[key],flush=True)
    years=["2024","2025","2026"]
    base=[x for y in years for x in ledgers[f"{y}_base"]]; stress=[x for y in years for x in ledgers[f"{y}_stress"]]
    aggregate=metrics(base,[{"equity":10000},{"equity":10000+sum(x["pnl"] for x in base)}])
    aggregate_stress=metrics(stress,[{"equity":10000},{"equity":10000+sum(x["pnl"] for x in stress)}])
    # Annual folds reset equity, so their summed ledger has no meaningful path drawdown.
    aggregate["max_drawdown_pct"]=None; aggregate_stress["max_drawdown_pct"]=None
    by_year={y:runs[f"{y}_base"]["net_pnl"] for y in years}; stress_by_year={y:runs[f"{y}_stress"]["net_pnl"] for y in years}
    monthly={}
    for x in base:
        key=dt.datetime.fromtimestamp(x["exit_timestamp"]/1000,UTC).strftime("%Y-%m")
        monthly[key]=monthly.get(key,0)+x["pnl"]
    positive_months=sum(max(0,v) for v in monthly.values())
    gates=dict(sample=aggregate["trades"]>=75,base_net=aggregate["net_pnl"]>0,
        base_expectancy=(aggregate["expectancy"] or 0)>0,base_pf=(aggregate["profit_factor"] or 0)>1.20,
        stress_net=aggregate_stress["net_pnl"]>0,stress_expectancy=(aggregate_stress["expectancy"] or 0)>0,
        stress_pf=(aggregate_stress["profit_factor"] or 0)>1.05,
        every_year=all(v>0 for v in by_year.values()),every_year_stress=all(v>0 for v in stress_by_year.values()),
        drawdown=max(runs["continuous_oos_base"]["max_drawdown_pct"],runs["continuous_oos_stress"]["max_drawdown_pct"])<=10,
        concentration=aggregate["net_pnl"]>0 and positive_months>0 and max(monthly.values(),default=0)<=.50*positive_months,
        audit=False,forward_paper=False)
    historical=all(v for k,v in gates.items() if k not in ("audit","forward_paper"))
    protocol=pathlib.Path("research/defi_yield_rotation_protocol_20261029.md")
    result=dict(strategy="DEFI_YIELD_ROTATION_XRP_V1",status="TEST NEDOKONCEN: audit and forward PAPER required" if historical else "NEPROSEL",
        protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),manifest=[ym]+pm,
        data_quality=dict(yield_rows=len(yields),yield_duplicates=ydup,yield_start=yields[0]["timestamp"],yield_end=yields[-1]["timestamp"],
            null_yields=0,price_rows=len(rows),price_duplicates=pdup,price_start=rows[0]["timestamp"],price_end=rows[-1]["timestamp"],
            price_gaps=gaps,eligible_yield_signals=len(signals),mapped_entry_dates=len(mapped),signals_after_price_history=after_prices),
        runs=runs,aggregate_oos=aggregate,aggregate_stress=aggregate_stress,by_year=by_year,stress_by_year=stress_by_year,
        monthly_base=monthly,gates=gates,historical_pass_before_audit=historical,
        limitations=["DefiLlama is a third-party aggregator and its history may be revised; hashes identify downloaded bytes, not publisher signatures.",
            "The current largest ordinary pool selection can carry survivorship bias; the pool and rules were frozen before returns.",
            "Daily OHLC cannot identify intrabar path; stop wins ambiguity and candle-low drawdown are conservative.",
            "Historical dates are exploratory and no independent forward PAPER evidence exists."])
    (dest/"results.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    with gzip.open(dest/"trades.json.gz","wt") as h: json.dump(ledgers,h)
    print(result["status"],gates,flush=True)

if __name__=="__main__": main()
