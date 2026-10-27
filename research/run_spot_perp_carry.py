"""Download real Binance archives and run the frozen XRP carry validation."""
import concurrent.futures, csv, gzip, hashlib, io, json, pathlib, sys, urllib.request, zipfile
from dataclasses import replace
from research.spot_perp_carry_v1 import Config, STEP, backtest, validate

MONTHS = [(y,m) for y in range(2022,2027) for m in range(1,13) if (y,m)<(2026,10)]

def get(url,path):
    if not path.exists():
        with urllib.request.urlopen(url,timeout=60) as response: path.write_bytes(response.read())
    return path.read_bytes()

def unpack_rows(payload,name):
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        members=z.namelist()
        if len(members)!=1: raise ValueError("unexpected archive members")
        return list(csv.reader(io.TextIOWrapper(z.open(members[0]))))

def fetch_price(job):
    kind,y,m,cache=job
    name=f"XRPUSDT-1h-{y}-{m:02d}.zip"
    middle="spot/monthly/klines" if kind=="spot" else "futures/um/monthly/markPriceKlines"
    url=f"https://data.binance.vision/data/{middle}/XRPUSDT/1h/{name}"
    payload=get(url,cache/f"{kind}-{name}"); rows=unpack_rows(payload,name)
    out=[]
    for row in rows:
        if row[0].lower().startswith("open"): continue
        t=int(row[0]); t=t//1000 if t>10**14 else t
        out.append(dict(timestamp=t,open=float(row[1]),high=float(row[2]),low=float(row[3]),close=float(row[4])))
    return kind,out,dict(kind=kind,url=url,sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload),rows=len(out))

def fetch_funding(job):
    y,m,cache=job; name=f"XRPUSDT-fundingRate-{y}-{m:02d}.zip"
    url=f"https://data.binance.vision/data/futures/um/monthly/fundingRate/XRPUSDT/{name}"
    payload=get(url,cache/f"funding-{name}")
    with zipfile.ZipFile(io.BytesIO(payload)) as z: rows=list(csv.DictReader(io.TextIOWrapper(z.open(z.namelist()[0]))))
    out=[]; offsets=[]
    for row in rows:
        raw=int(row["calc_time"]); nominal=round(raw/STEP)*STEP; offset=raw-nominal
        if abs(offset)>1000: raise ValueError("funding offset")
        offsets.append(offset); out.append(dict(timestamp=nominal,rate=float(row["last_funding_rate"])))
    return out,dict(kind="funding",url=url,sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload),rows=len(out),adjusted=sum(x!=0 for x in offsets),max_abs_adjustment_ms=max(map(abs,offsets),default=0))

def stamp(y,m=1):
    import datetime
    return int(datetime.datetime(y,m,1,tzinfo=datetime.timezone.utc).timestamp()*1000)

def folds():
    return [("2022_control",stamp(2022),stamp(2023)),("2023",stamp(2023),stamp(2024)),("2024",stamp(2024),stamp(2025)),("2025",stamp(2025),stamp(2026)),("2026",stamp(2026),stamp(2026,10)),("continuous_oos",stamp(2023),stamp(2026,10))]

def metrics(trades,curve,initial=10000):
    gains=sum(max(0,t["pnl"]) for t in trades); losses=-sum(min(0,t["pnl"]) for t in trades)
    peak=initial; dd=0
    for x in curve:
        peak=max(peak,x["equity"]); dd=max(dd,(peak-x["equity"])/peak*100 if peak else 0)
    net=sum(t["pnl"] for t in trades)
    return dict(trades=len(trades),net_pnl=net,net_return_pct=net/initial*100,profit_factor=gains/losses if losses else None,expectancy=net/len(trades) if trades else None,max_drawdown_pct=dd,total_funding=sum(t["funding_cash"] for t in trades),fees=sum(t["fees"] for t in trades),slippage_cost=sum(t["slippage_cost"] for t in trades))

def main():
    cache=pathlib.Path(sys.argv[1]); cache.mkdir(parents=True,exist_ok=True)
    dest=pathlib.Path(sys.argv[2]); dest.mkdir(parents=True,exist_ok=True)
    price_jobs=[(k,y,m,cache) for k in ("spot","mark") for y,m in MONTHS]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        prices=list(pool.map(fetch_price,price_jobs)); fund_chunks=list(pool.map(fetch_funding,[(y,m,cache) for y,m in MONTHS]))
    maps={"spot":{},"mark":{}}; raw_counts={"spot":0,"mark":0}
    for kind,rows,_ in prices:
        raw_counts[kind]+=len(rows); maps[kind].update({x["timestamp"]:x for x in rows})
    common=sorted(set(maps["spot"])&set(maps["mark"]))
    bars=[]
    for t in common:
        row={"timestamp":t}
        for kind in ("spot","mark"):
            row.update({f"{kind}_{k}":maps[kind][t][k] for k in ("open","high","low","close")})
        bars.append(row)
    raw_funding=[x for chunk,_ in fund_chunks for x in chunk]; funding_map={x["timestamp"]:x for x in raw_funding}; funding=[funding_map[t] for t in sorted(funding_map)]
    validate(bars,funding)
    quality=dict(spot_duplicates=raw_counts["spot"]-len(maps["spot"]),mark_duplicates=raw_counts["mark"]-len(maps["mark"]),funding_duplicates=len(raw_funding)-len(funding_map),spot_only_hours=len(set(maps["spot"])-set(maps["mark"])),mark_only_hours=len(set(maps["mark"])-set(maps["spot"])),aligned_hours=len(bars),aligned_gaps=[dict(after=a["timestamp"],before=b["timestamp"],missing_hours=(b["timestamp"]-a["timestamp"])//STEP-1) for a,b in zip(bars,bars[1:]) if b["timestamp"]-a["timestamp"]!=STEP])
    runs={}; ledger={}
    for name,start,end in folds():
        for label,mult in (("base",1),("stress",2)):
            cfg=replace(Config(),spot_fee=Config().spot_fee*mult,perp_fee=Config().perp_fee*mult,slippage=Config().slippage*mult)
            trades,curve=backtest(bars,funding,start,end,cfg); key=f"{name}_{label}"
            runs[key]=metrics(trades,curve); ledger[key]=trades; print(key,runs[key],flush=True)
    years=["2023","2024","2025","2026"]
    base=[t for y in years for t in ledger[f"{y}_base"]]; stress=[t for y in years for t in ledger[f"{y}_stress"]]
    base_summary=metrics(base,[{"timestamp":0,"equity":10000},{"timestamp":1,"equity":10000+sum(t["pnl"] for t in base)}]); stress_summary=metrics(stress,[{"timestamp":0,"equity":10000},{"timestamp":1,"equity":10000+sum(t["pnl"] for t in stress)}])
    by_year={y:runs[f"{y}_base"]["net_pnl"] for y in years}; stress_by_year={y:runs[f"{y}_stress"]["net_pnl"] for y in years}; positive=sum(max(0,x) for x in by_year.values())
    gates=dict(sample=base_summary["trades"]>=60,base_net=base_summary["net_pnl"]>0,base_expectancy=(base_summary["expectancy"] or 0)>0,base_pf=(base_summary["profit_factor"] or 0)>1.15,stress_net=stress_summary["net_pnl"]>0,stress_expectancy=(stress_summary["expectancy"] or 0)>0,stress_pf=(stress_summary["profit_factor"] or 0)>1.02,three_positive_years=sum(x>0 for x in by_year.values())>=3,final_year=by_year["2026"]>0,three_positive_stress_years=sum(x>0 for x in stress_by_year.values())>=3,drawdown=max(runs["continuous_oos_base"]["max_drawdown_pct"],runs["continuous_oos_stress"]["max_drawdown_pct"])<=10,concentration=base_summary["net_pnl"]>0 and positive>0 and max(by_year.values())<=0.40*positive)
    historical_pass=all(gates.values())
    protocol=pathlib.Path("research/spot_perp_carry_protocol.md")
    result=dict(strategy="XRP_SPOT_PERP_CARRY_V1",status="TEST NEDOKONCEN: independent forward PAPER evidence required" if historical_pass else "NEPROSEL",protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),manifest=[x[2] for x in prices]+[x[1] for x in fund_chunks],data_quality=quality,runs=runs,aggregate_oos=base_summary,aggregate_stress=stress_summary,by_year=by_year,stress_by_year=stress_by_year,gates=gates,historical_pass=historical_pass,limitations=["Exploratory historical evidence; previously observed dates are not untouched.","Local SHA256 fingerprints identify downloaded bytes and are not publisher signatures.","Mark-price klines proxy the perpetual leg; executable bid/ask and liquidation mechanics are unavailable.","Intrabar stop uses adverse independent mark-high and spot-low extrema and is conservative but not tick-exact.","No interest on idle cash, spot custody yield, taxes, or counterparty failure is modelled.","No independent forward PAPER evidence exists."])
    (dest/"results.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    with gzip.open(dest/"trades.json.gz","wt") as h: json.dump(ledger,h)
    print(result["status"],gates,flush=True)

if __name__=="__main__": main()

