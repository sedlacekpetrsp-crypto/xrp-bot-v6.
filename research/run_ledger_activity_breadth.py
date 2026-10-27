"""Download direct CoinMetrics/Binance data and evaluate frozen on-chain rules."""
import csv,gzip,hashlib,io,json,pathlib,sys,urllib.parse,urllib.request,zipfile,datetime as dt
from dataclasses import replace
from research.ledger_activity_breadth_v1 import Config,DAY,backtest,validate

MONTHS=[(y,m) for y in range(2022,2027) for m in range(1,13) if (y,m)<(2026,10)]
UTC=dt.timezone.utc
def get(url,path):
    if not path.exists():
        req=urllib.request.Request(url,headers={"User-Agent":"xrp-research/1.0"})
        with urllib.request.urlopen(req,timeout=120) as r:path.write_bytes(r.read())
    return path.read_bytes()
def stamp(y,m=1):return int(dt.datetime(y,m,1,tzinfo=UTC).timestamp()*1000)

def fetch_metrics(cache):
    q=urllib.parse.urlencode(dict(assets="xrp",metrics="TxCnt,AdrActCnt",frequency="1d",start_time="2022-01-01",end_time="2026-10-01",page_size=10000))
    url=f"https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?{q}"; payload=get(url,cache/"coinmetrics-xrp-daily.json"); obj=json.loads(payload)
    if "error" in obj or obj.get("next_page_token"):raise ValueError(f"CoinMetrics response incomplete {obj.get('error') or obj.get('next_page_token')}")
    rows=[]
    for x in obj["data"]:
        t=int(dt.datetime.fromisoformat(x["time"].replace("Z","+00:00")).timestamp()*1000)
        rows.append(dict(timestamp=t,active_addresses=float(x["AdrActCnt"]),tx_count=float(x["TxCnt"])))
    return rows,dict(kind="coinmetrics_xrp_activity",url=url,sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload),rows=len(rows))

def fetch_prices(cache):
    allrows=[]; manifest=[]
    for y,m in MONTHS:
        name=f"XRPUSDT-1d-{y}-{m:02d}.zip"; url=f"https://data.binance.vision/data/spot/monthly/klines/XRPUSDT/1d/{name}"; payload=get(url,cache/name)
        with zipfile.ZipFile(io.BytesIO(payload)) as z: rows=list(csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]))))
        out=[]
        for x in rows:
            if x[0].lower().startswith("open"):continue
            t=int(x[0]);t=t//1000 if t>10**14 else t
            out.append(dict(timestamp=t,open=float(x[1]),high=float(x[2]),low=float(x[3]),close=float(x[4])))
        allrows+=out;manifest.append(dict(kind="binance_XRPUSDT_1d",url=url,sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload),rows=len(out)))
    return allrows,manifest

def unique(rows,label):
    d={};dup=0
    for x in rows:
        if x["timestamp"] in d:
            if d[x["timestamp"]]!=x:raise ValueError(f"conflicting duplicate {label}")
            dup+=1
        d[x["timestamp"]]=x
    return d,dup
def folds():return [("2022_control",stamp(2022),stamp(2023)),("2023",stamp(2023),stamp(2024)),("2024",stamp(2024),stamp(2025)),("2025",stamp(2025),stamp(2026)),("2026",stamp(2026),stamp(2026,10)),("continuous_oos",stamp(2023),stamp(2026,10))]
def metrics(trades,curve,initial=10000):
    gains=sum(max(0,x["pnl"]) for x in trades);losses=-sum(min(0,x["pnl"]) for x in trades);net=sum(x["pnl"] for x in trades);peak=initial;dd=0
    for x in curve:peak=max(peak,x["equity"]);dd=max(dd,(peak-x["equity"])/peak*100)
    return dict(trades=len(trades),net_pnl=net,net_return_pct=net/initial*100,profit_factor=gains/losses if losses else None,expectancy=net/len(trades) if trades else None,max_drawdown_pct=dd,fees=sum(x["fees"] for x in trades),slippage_cost=sum(x["slippage_cost"] for x in trades))

def main():
    cache=pathlib.Path(sys.argv[1]);cache.mkdir(parents=True,exist_ok=True);dest=pathlib.Path(sys.argv[2]);dest.mkdir(parents=True,exist_ok=True)
    mr,mm=fetch_metrics(cache);pr,pm=fetch_prices(cache);mmap,md=unique(mr,"metrics");pmap,pd=unique(pr,"prices");common=sorted(set(mmap)&set(pmap));rows=[]
    for t in common:rows.append({**pmap[t],**mmap[t]})
    validate(rows)
    quality=dict(metric_rows=len(mmap),price_rows=len(pmap),aligned_days=len(rows),metric_duplicates=md,price_duplicates=pd,metric_only=len(set(mmap)-set(pmap)),price_only=len(set(pmap)-set(mmap)),gaps=[dict(after=a["timestamp"],before=b["timestamp"],missing_days=(b["timestamp"]-a["timestamp"])//DAY-1) for a,b in zip(rows,rows[1:]) if b["timestamp"]-a["timestamp"]!=DAY])
    runs={};ledger={}
    for name,start,end in folds():
        for label,mult in (("base",1),("stress",2)):
            base=Config();cfg=replace(base,fee=base.fee*mult,slippage=base.slippage*mult);tr,curve=backtest(rows,start,end,cfg);key=f"{name}_{label}";runs[key]=metrics(tr,curve);ledger[key]=tr;print(key,runs[key],flush=True)
    years=["2023","2024","2025","2026"];base=[x for y in years for x in ledger[f"{y}_base"]];stress=[x for y in years for x in ledger[f"{y}_stress"]]
    bm=metrics(base,[{"timestamp":0,"equity":10000},{"timestamp":1,"equity":10000+sum(x["pnl"] for x in base)}]);sm=metrics(stress,[{"timestamp":0,"equity":10000},{"timestamp":1,"equity":10000+sum(x["pnl"] for x in stress)}]);by={y:runs[f"{y}_base"]["net_pnl"] for y in years};sy={y:runs[f"{y}_stress"]["net_pnl"] for y in years}
    monthly={}
    for x in base:
        k=dt.datetime.fromtimestamp(x["exit_timestamp"]/1000,UTC).strftime("%Y-%m");monthly[k]=monthly.get(k,0)+x["pnl"]
    pos=sum(max(0,x) for x in monthly.values())
    gates=dict(sample=bm["trades"]>=80,base_net=bm["net_pnl"]>0,base_expectancy=(bm["expectancy"] or 0)>0,base_pf=(bm["profit_factor"] or 0)>1.15,stress_net=sm["net_pnl"]>0,stress_expectancy=(sm["expectancy"] or 0)>0,stress_pf=(sm["profit_factor"] or 0)>1.02,three_positive_years=sum(x>0 for x in by.values())>=3,three_positive_stress_years=sum(x>0 for x in sy.values())>=3,final_year=by["2026"]>0 and sy["2026"]>0,drawdown=max(runs["continuous_oos_base"]["max_drawdown_pct"],runs["continuous_oos_stress"]["max_drawdown_pct"])<=10,concentration=bm["net_pnl"]>0 and pos>0 and max(monthly.values(),default=0)<=.25*pos)
    hp=all(gates.values());protocol=pathlib.Path("research/ledger_activity_breadth_protocol.md")
    result=dict(strategy="XRP_LEDGER_ACTIVITY_BREADTH_V1",status="TEST NEDOKONCEN: independent forward PAPER evidence required" if hp else "NEPROSEL",protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),manifest=[mm]+pm,data_quality=quality,runs=runs,aggregate_oos=bm,aggregate_stress=sm,by_year=by,stress_by_year=sy,monthly_base=monthly,gates=gates,historical_pass=hp,limitations=["CoinMetrics Community observations are third-party derived on-chain metrics; response bytes are locally hashed, not publisher-signed.","A full-day publication lag is imposed to avoid same-day aggregate leakage.","Daily OHLC cannot determine intraday path; stop wins ambiguity and drawdown marks the daily low.","Historical dates are exploratory and not untouched validation.","No independent forward PAPER evidence exists."])
    (dest/"results.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    with gzip.open(dest/"trades.json.gz","wt") as h:json.dump(ledger,h)
    print(result["status"],gates,flush=True)
if __name__=="__main__":main()
