"""Download direct Coinbase/Binance history and evaluate the frozen protocol."""
import concurrent.futures, csv, datetime as dt, gzip, hashlib, io, json, pathlib, sys, time, urllib.parse, urllib.request, zipfile
from dataclasses import replace
from research.cross_exchange_residual_v1 import Config, STEP, backtest, validate

UTC=dt.timezone.utc
START=dt.datetime(2023,7,1,tzinfo=UTC); END=dt.datetime(2026,10,1,tzinfo=UTC)
MONTHS=[]
cur=START.replace(day=1)
while cur<END:
    MONTHS.append((cur.year,cur.month)); cur=(cur.replace(day=28)+dt.timedelta(days=4)).replace(day=1)

def get(url,path,headers=None,retries=6):
    if path.exists(): return path.read_bytes()
    for n in range(retries):
        try:
            req=urllib.request.Request(url,headers=headers or {"User-Agent":"xrp-research/1.0"})
            with urllib.request.urlopen(req,timeout=90) as r: payload=r.read()
            path.write_bytes(payload); return payload
        except Exception:
            if n+1==retries: raise
            time.sleep(2**n)

def coinbase_chunks():
    out=[]; s=START
    while s<END:
        e=min(s+dt.timedelta(hours=289),END-dt.timedelta(hours=1)); out.append((s,e)); s=e+dt.timedelta(hours=1)
    return out

def fetch_coinbase(job):
    product,s,e,cache=job
    key=f"coinbase-{product}-{s:%Y%m%d%H}-{e:%Y%m%d%H}.json"
    q=urllib.parse.urlencode(dict(granularity=3600,start=s.isoformat().replace('+00:00','Z'),end=e.isoformat().replace('+00:00','Z')))
    url=f"https://api.exchange.coinbase.com/products/{product}/candles?{q}"
    payload=get(url,cache/key); raw=json.loads(payload)
    if isinstance(raw,dict): raise ValueError(f"Coinbase error {raw}")
    rows=[]
    for x in raw:
        if len(x)!=6: raise ValueError("Coinbase row")
        t=int(x[0])*1000; rows.append(dict(timestamp=t,low=float(x[1]),high=float(x[2]),open=float(x[3]),close=float(x[4])))
    return product,rows,dict(kind=f"coinbase_{product}",url=url,sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload),rows=len(rows))

def unzip(payload):
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        if len(z.namelist())!=1: raise ValueError("archive members")
        return list(csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]))))

def fetch_binance(job):
    kind,symbol,y,m,cache=job
    name=f"{symbol}-1h-{y}-{m:02d}.zip"
    mid="futures/um/monthly/markPriceKlines" if kind=="mark" else "spot/monthly/klines"
    url=f"https://data.binance.vision/data/{mid}/{symbol}/1h/{name}"
    payload=get(url,cache/f"{kind}-{name}"); rows=[]
    for x in unzip(payload):
        if x[0].lower().startswith("open"): continue
        t=int(x[0]); t=t//1000 if t>10**14 else t
        rows.append(dict(timestamp=t,open=float(x[1]),high=float(x[2]),low=float(x[3]),close=float(x[4])))
    return kind,symbol,rows,dict(kind=f"binance_{kind}_{symbol}",url=url,sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload),rows=len(rows))

def fetch_funding(job):
    y,m,cache=job; name=f"XRPUSDT-fundingRate-{y}-{m:02d}.zip"
    url=f"https://data.binance.vision/data/futures/um/monthly/fundingRate/XRPUSDT/{name}"
    payload=get(url,cache/f"funding-{name}")
    with zipfile.ZipFile(io.BytesIO(payload)) as z: rows=list(csv.DictReader(io.TextIOWrapper(z.open(z.namelist()[0]))))
    out=[]; offsets=[]
    for x in rows:
        raw=int(x["calc_time"]); nominal=round(raw/STEP)*STEP; offsets.append(raw-nominal)
        if abs(raw-nominal)>1000: raise ValueError("funding offset")
        out.append(dict(timestamp=nominal,rate=float(x["last_funding_rate"])))
    return out,dict(kind="binance_funding_XRPUSDT",url=url,sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload),rows=len(out),adjusted=sum(x!=0 for x in offsets),max_abs_adjustment_ms=max(map(abs,offsets),default=0))

def merge_unique(chunks,label):
    out={}; dup=0
    for rows in chunks:
        for x in rows:
            t=x["timestamp"]
            if t in out:
                if out[t]!=x: raise ValueError(f"conflicting duplicate {label} {t}")
                dup+=1
            out[t]=x
    return out,dup

def stamp(y,m,d=1): return int(dt.datetime(y,m,d,tzinfo=UTC).timestamp()*1000)
def folds():
    x=[("2023_H2_control",stamp(2023,7),stamp(2024,1))]
    for y in (2024,2025,2026):
        for q,m in enumerate((1,4,7,10),1):
            if (y,m)>=(2026,10): continue
            ey,em=(y+1,1) if m==10 else (y,m+3); x.append((f"{y}_Q{q}",stamp(y,m),stamp(ey,em)))
    x.append(("continuous_oos",stamp(2024,1),stamp(2026,10))); return x

def metrics(trades,curve,initial=10000):
    gains=sum(max(0,t["pnl"]) for t in trades); losses=-sum(min(0,t["pnl"]) for t in trades); net=sum(t["pnl"] for t in trades)
    peak=initial; dd=0
    for p in curve:
        peak=max(peak,p["equity"]); dd=max(dd,(peak-p["equity"])/peak*100)
    return dict(trades=len(trades),net_pnl=net,net_return_pct=net/initial*100,profit_factor=gains/losses if losses else None,expectancy=net/len(trades) if trades else None,max_drawdown_pct=dd,fees=sum(t["fees"] for t in trades),slippage_cost=sum(t["slippage_cost"] for t in trades),funding_cash=sum(t["funding_cash"] for t in trades))

def main():
    cache=pathlib.Path(sys.argv[1]); cache.mkdir(parents=True,exist_ok=True); dest=pathlib.Path(sys.argv[2]); dest.mkdir(parents=True,exist_ok=True)
    cj=[(p,s,e,cache) for p in ("XRP-USD","BTC-USD") for s,e in coinbase_chunks()]
    bj=[("mark","XRPUSDT",y,m,cache) for y,m in MONTHS]+[("spot","BTCUSDT",y,m,cache) for y,m in MONTHS]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        cres=list(pool.map(fetch_coinbase,cj)); bres=list(pool.map(fetch_binance,bj)); fres=list(pool.map(fetch_funding,[(y,m,cache) for y,m in MONTHS]))
    cmaps={}; duplicates={}
    for product in ("XRP-USD","BTC-USD"):
        cmaps[product],duplicates[product]=merge_unique([x[1] for x in cres if x[0]==product],product)
    bmaps={}
    for kind,symbol in (("mark","XRPUSDT"),("spot","BTCUSDT")):
        bmaps[(kind,symbol)],duplicates[f"{kind}_{symbol}"]=merge_unique([x[2] for x in bres if x[0]==kind and x[1]==symbol],f"{kind}_{symbol}")
    sets=[set(cmaps["XRP-USD"]),set(cmaps["BTC-USD"]),set(bmaps[("mark","XRPUSDT")]),set(bmaps[("spot","BTCUSDT")])]; common=sorted(set.intersection(*sets))
    bars=[]
    for t in common:
        b={"timestamp":t}
        for prefix,row in (("cxrp",cmaps["XRP-USD"][t]),("cbtc",cmaps["BTC-USD"][t]),("bxrp",bmaps[("mark","XRPUSDT")][t]),("bbtc",bmaps[("spot","BTCUSDT")][t])):
            b.update({f"{prefix}_{k}":row[k] for k in ("open","high","low","close")})
        bars.append(b)
    rawf=[x for chunk,_ in fres for x in chunk]; fmap={x["timestamp"]:x for x in rawf}; funding=[fmap[t] for t in sorted(fmap)]
    validate(bars,funding)
    quality=dict(series_counts={"coinbase_XRPUSD":len(cmaps["XRP-USD"]),"coinbase_BTCUSD":len(cmaps["BTC-USD"]),"binance_XRP_mark":len(bmaps[("mark","XRPUSDT")]),"binance_BTC_spot":len(bmaps[("spot","BTCUSDT")])},duplicates=duplicates,funding_duplicates=len(rawf)-len(fmap),aligned_hours=len(bars),excluded_by_series={"coinbase_XRPUSD":len(sets[0]-set(common)),"coinbase_BTCUSD":len(sets[1]-set(common)),"binance_XRP_mark":len(sets[2]-set(common)),"binance_BTC_spot":len(sets[3]-set(common))},aligned_gaps=[dict(after=a["timestamp"],before=b["timestamp"],missing_hours=(b["timestamp"]-a["timestamp"])//STEP-1) for a,b in zip(bars,bars[1:]) if b["timestamp"]-a["timestamp"]!=STEP])
    runs={}; ledger={}
    for name,start,end in folds():
        for label,mult in (("base",1),("stress",2)):
            base=Config(); cfg=replace(base,coinbase_fee=base.coinbase_fee*mult,binance_fee=base.binance_fee*mult,coinbase_slippage=base.coinbase_slippage*mult,binance_slippage=base.binance_slippage*mult)
            tr,curve=backtest(bars,funding,start,end,cfg); key=f"{name}_{label}"; ledger[key]=tr; runs[key]=metrics(tr,curve); print(key,runs[key],flush=True)
    qs=[x[0] for x in folds() if x[0] not in ("2023_H2_control","continuous_oos")]
    base=[t for q in qs for t in ledger[f"{q}_base"]]; stress=[t for q in qs for t in ledger[f"{q}_stress"]]
    bm=metrics(base,[{"timestamp":0,"equity":10000},{"timestamp":1,"equity":10000+sum(t["pnl"] for t in base)}]); sm=metrics(stress,[{"timestamp":0,"equity":10000},{"timestamp":1,"equity":10000+sum(t["pnl"] for t in stress)}])
    bq={q:runs[f"{q}_base"]["net_pnl"] for q in qs}; sq={q:runs[f"{q}_stress"]["net_pnl"] for q in qs}; pos=sum(max(0,x) for x in bq.values())
    gates=dict(sample=bm["trades"]>=120,base_net=bm["net_pnl"]>0,base_expectancy=(bm["expectancy"] or 0)>0,base_pf=(bm["profit_factor"] or 0)>1.15,stress_net=sm["net_pnl"]>0,stress_expectancy=(sm["expectancy"] or 0)>0,stress_pf=(sm["profit_factor"] or 0)>1.02,seven_positive_quarters=sum(x>0 for x in bq.values())>=7,seven_positive_stress_quarters=sum(x>0 for x in sq.values())>=7,final_quarter=bq["2026_Q3"]>0 and sq["2026_Q3"]>0,drawdown=max(runs["continuous_oos_base"]["max_drawdown_pct"],runs["continuous_oos_stress"]["max_drawdown_pct"])<=10,concentration=bm["net_pnl"]>0 and pos>0 and max(bq.values())<=.30*pos)
    hp=all(gates.values()); protocol=pathlib.Path("research/cross_exchange_residual_protocol.md")
    result=dict(strategy="XRP_CROSS_EXCHANGE_RESIDUAL_CONVERGENCE_V1",status="TEST NEDOKONCEN: independent forward PAPER evidence required" if hp else "NEPROSEL",protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),manifest=[x[2] for x in cres]+[x[3] for x in bres]+[x[1] for x in fres],data_quality=quality,runs=runs,aggregate_oos=bm,aggregate_stress=sm,by_quarter=bq,stress_by_quarter=sq,gates=gates,historical_pass=hp,limitations=["Exploratory history; dates are not untouched validation.","Coinbase candles are requested in bounded chunks; payload SHA256 values are local fingerprints, not publisher signatures.","Hourly OHLC cannot reproduce synchronized executable bid/ask or the intrabar path.","Conservative independent OHLC extremes can overstate stop loss and drawdown.","Coinbase fee is a frozen conservative taker assumption and actual account tier may differ.","No independent forward PAPER evidence exists."])
    (dest/"results.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    with gzip.open(dest/"trades.json.gz","wt") as h: json.dump(ledger,h)
    print(result["status"],gates,flush=True)

if __name__=="__main__": main()
