import csv,datetime as dt,gzip,hashlib,io,json,pathlib,sys,urllib.parse,urllib.request,zipfile
from dataclasses import replace
from research.btc_asset_manager_accumulation_xrp_v1 import Config,DAY,backtest,make_signals,validate_prices,validate_reports
UTC=dt.timezone.utc
CFTC="https://www.cftc.gov/files/dea/history/fut_fin_txt_{year}.zip"
BINANCE="https://data-api.binance.vision/api/v3/klines"
def stamp(y,m=1,d=1): return int(dt.datetime(y,m,d,tzinfo=UTC).timestamp()*1000)
def get(url,path):
    if not path.exists():
        with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"xrp-research/1.0"}),timeout=180) as r: path.write_bytes(r.read())
    return path.read_bytes()
def integer(row,key):
    value=row.get(key,"").strip()
    if not value or value==".": raise ValueError(f"missing {key}")
    return int(value)
def load_reports(cache):
    reports=[]; manifest=[]
    for year in range(2018,2027):
        url=CFTC.format(year=year); path=cache/f"cftc-financial-futures-{year}.zip"; raw=get(url,path)
        z=zipfile.ZipFile(io.BytesIO(raw)); names=z.namelist()
        if len(names)!=1: raise ValueError("unexpected CFTC zip members")
        content=z.read(names[0]); rows=list(csv.DictReader(io.StringIO(content.decode("latin1"))))
        selected=[]
        for row in rows:
            if row.get("CFTC_Contract_Market_Code","").strip()!="133741" or row.get("FutOnly_or_Combined","").strip()!="FutOnly": continue
            if row.get("Market_and_Exchange_Names","").strip()!="BITCOIN - CHICAGO MERCANTILE EXCHANGE": raise ValueError("unexpected main contract name")
            day=dt.date.fromisoformat(row["Report_Date_as_YYYY-MM-DD"].strip())
            selected.append(dict(timestamp=int(dt.datetime(day.year,day.month,day.day,tzinfo=UTC).timestamp()*1000),open_interest=integer(row,"Open_Interest_All"),asset_manager_long=integer(row,"Asset_Mgr_Positions_Long_All"),asset_manager_short=integer(row,"Asset_Mgr_Positions_Short_All")))
        reports.extend(selected)
        manifest.append(dict(kind="CFTC_TFF_futures_only",year=year,url=url,cache_file=path.name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),archive_member=names[0],archive_member_sha256=hashlib.sha256(content).hexdigest(),all_rows=len(rows),selected_rows=len(selected)))
    reports.sort(key=lambda x:x["timestamp"]); validate_reports(reports)
    return reports,manifest
def load_prices(cache):
    cursor,end,page=stamp(2020),stamp(2026,10)-1,0; rows=[]; manifest=[]
    while cursor<=end:
        url=BINANCE+"?"+urllib.parse.urlencode(dict(symbol="XRPUSDT",interval="1d",startTime=cursor,endTime=end,limit=1000)); path=cache/f"XRPUSDT-1d-cftc-api-{page}.json"; raw=get(url,path); doc=json.loads(raw)
        manifest.append(dict(kind="binance_XRPUSDT_1d",url=url,cache_file=path.name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),rows=len(doc)))
        if not doc: break
        rows += [dict(timestamp=int(x[0]),open=float(x[1]),high=float(x[2]),low=float(x[3]),close=float(x[4])) for x in doc]
        cursor=int(doc[-1][0])+DAY; page+=1
        if len(doc)<1000: break
    validate_prices(rows); return rows,manifest
def metrics(trades,curve,initial=10_000.):
    wins=sum(max(0,x["pnl"]) for x in trades); losses=-sum(min(0,x["pnl"]) for x in trades); net=sum(x["pnl"] for x in trades); peak=initial; dd=0
    for p in curve: peak=max(peak,p["equity"]); dd=max(dd,(peak-p["equity"])/peak*100)
    return dict(trades=len(trades),net_pnl=net,net_return_pct=net/initial*100,profit_factor=wins/losses if losses else None,expectancy=net/len(trades) if trades else None,max_drawdown_pct=dd,fees=sum(x["fees"] for x in trades),slippage_cost=sum(x["slippage_cost"] for x in trades),gross_profit=wins,gross_loss=losses)
def main():
    cache,dest=map(pathlib.Path,sys.argv[1:3]); cache.mkdir(parents=True,exist_ok=True); dest.mkdir(parents=True,exist_ok=True)
    reports,cmanifest=load_reports(cache); prices,pmanifest=load_prices(cache); signals=make_signals(reports)
    folds=[("2020_2021_control",stamp(2020),stamp(2022))]+[(str(y),stamp(y),stamp(y+1) if y<2026 else stamp(2026,10)) for y in range(2022,2027)]+[("continuous_oos",stamp(2022),stamp(2026,10))]
    runs={}; ledgers={}
    for name,start,end in folds:
        for label,m in (("base",1),("stress",2)):
            c=replace(Config(),fee=Config().fee*m,slippage=Config().slippage*m); trades,curve=backtest(prices,signals,start,end,c); key=name+"_"+label; ledgers[key]=trades; runs[key]=metrics(trades,curve); print(key,runs[key],flush=True)
    years=[str(y) for y in range(2022,2027)]; base=[x for y in years for x in ledgers[y+"_base"]]; stress=[x for y in years for x in ledgers[y+"_stress"]]
    aggregate,aggregate_stress=metrics(base,[]),metrics(stress,[]); aggregate["max_drawdown_pct"]=None; aggregate_stress["max_drawdown_pct"]=None
    by_year={y:runs[y+"_base"]["net_pnl"] for y in years}; stress_by_year={y:runs[y+"_stress"]["net_pnl"] for y in years}; monthly={}
    for t in base:
        key=dt.datetime.fromtimestamp(t["exit_timestamp"]/1000,UTC).strftime("%Y-%m"); monthly[key]=monthly.get(key,0)+t["pnl"]
    positive=sum(max(0,x) for x in monthly.values()); concentration=max((max(0,x)/positive for x in monthly.values()),default=1.)
    gates=dict(sample=aggregate["trades"]>=75,base_net=aggregate["net_pnl"]>0,base_expectancy=(aggregate["expectancy"] or 0)>0,base_pf=(aggregate["profit_factor"] or 0)>1.20,stress_net=aggregate_stress["net_pnl"]>0,stress_expectancy=(aggregate_stress["expectancy"] or 0)>0,stress_pf=(aggregate_stress["profit_factor"] or 0)>1.05,four_years=sum(x>0 for x in by_year.values())>=4,four_years_stress=sum(x>0 for x in stress_by_year.values())>=4,final_year=by_year["2026"]>0 and stress_by_year["2026"]>0,drawdown=max(runs["continuous_oos_base"]["max_drawdown_pct"],runs["continuous_oos_stress"]["max_drawdown_pct"])<=10,concentration=aggregate["net_pnl"]>0 and positive>0 and concentration<=.25,audit=False,forward_paper=False)
    historical=all(v for k,v in gates.items() if k not in ("audit","forward_paper")); protocol=pathlib.Path("research/btc_asset_manager_accumulation_xrp_protocol_20261104.md")
    result=dict(strategy="BTC_ASSET_MANAGER_ACCUMULATION_XRP_V1",status="TEST NEDOKONCEN: audit and forward PAPER required" if historical else "NEPROSEL",protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),manifest=cmanifest+pmanifest,data_quality=dict(report_rows=len(reports),report_start=reports[0]["timestamp"],report_end=reports[-1]["timestamp"],report_duplicates=0,price_rows=len(prices),price_start=prices[0]["timestamp"],price_end=prices[-1]["timestamp"],price_gaps=[]),signals_total=len(signals),runs=runs,aggregate_oos=aggregate,aggregate_stress=aggregate_stress,by_year=by_year,stress_by_year=stress_by_year,monthly_base=monthly,positive_month_profit_concentration=concentration,gates=gates,historical_pass_before_audit=historical,limitations=["CFTC historical archives can contain revised rather than point-in-time vintage records.","Asset-manager category can include heterogeneous mandates and futures hedges.","Daily XRP OHLC cannot reconstruct tick paths; fixed conservative rules apply.","Local SHA256 values are provenance hashes, not publisher signatures.","No independent forward PAPER evidence exists."])
    (dest/"results.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n");
    with gzip.open(dest/"reports.json.gz","wt") as h: json.dump(reports,h)
    with gzip.open(dest/"trades.json.gz","wt") as h: json.dump(ledgers,h)
    print(result["status"],gates,flush=True)
if __name__=="__main__": main()
