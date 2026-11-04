import csv,datetime as dt,gzip,hashlib,io,json,pathlib,statistics,sys,zipfile
DAY=86_400_000; UTC=dt.timezone.utc
def close(a,b,tol=1e-8): return abs(a-b)<=tol*max(1,abs(a),abs(b))
def next_monday(ts):
    d=dt.datetime.fromtimestamp(ts/1000,UTC); n=(7-d.weekday())%7; return ts+(7 if n==0 else n)*DAY
def main():
    cache,dest=map(pathlib.Path,sys.argv[1:3]); result=json.loads((dest/"results.json").read_text()); checks=[]
    def check(name,value): checks.append(dict(name=name,passed=bool(value)))
    reports=[]
    for item in result["manifest"]:
        raw=(cache/item["cache_file"]).read_bytes(); check("hash_"+item["cache_file"],hashlib.sha256(raw).hexdigest()==item["sha256"] and len(raw)==item["bytes"])
        if item["kind"]!="CFTC_TFF_futures_only": continue
        z=zipfile.ZipFile(io.BytesIO(raw)); content=z.read(item["archive_member"]); check("member_hash_"+str(item["year"]),hashlib.sha256(content).hexdigest()==item["archive_member_sha256"])
        rows=list(csv.DictReader(io.StringIO(content.decode("latin1")))); selected=[]
        for r in rows:
            if r.get("CFTC_Contract_Market_Code","").strip()=="133741" and r.get("FutOnly_or_Combined","").strip()=="FutOnly":
                check("contract_name_"+r["Report_Date_as_YYYY-MM-DD"],r["Market_and_Exchange_Names"].strip()=="BITCOIN - CHICAGO MERCANTILE EXCHANGE")
                d=dt.date.fromisoformat(r["Report_Date_as_YYYY-MM-DD"].strip()); selected.append(dict(timestamp=int(dt.datetime(d.year,d.month,d.day,tzinfo=UTC).timestamp()*1000),open_interest=int(r["Open_Interest_All"]),asset_manager_long=int(r["Asset_Mgr_Positions_Long_All"]),asset_manager_short=int(r["Asset_Mgr_Positions_Short_All"])))
        check("selected_rows_"+str(item["year"]),len(selected)==item["selected_rows"]); reports+=selected
    reports.sort(key=lambda x:x["timestamp"]); check("report_rows",len(reports)==result["data_quality"]["report_rows"]); check("reports_unique_ordered",len({x["timestamp"] for x in reports})==len(reports) and all(b["timestamp"]>a["timestamp"] for a,b in zip(reports,reports[1:])))
    with gzip.open(dest/"reports.json.gz","rt") as h: check("reports_exact",json.load(h)==reports)
    shares=[(x["asset_manager_long"]-x["asset_manager_short"])/x["open_interest"] for x in reports]; signals={}
    for i in range(52,len(reports)):
        current=shares[i]; median=statistics.median(shares[i-52:i])
        if current>median and current>shares[i-4]:
            entry=next_monday(reports[i]["timestamp"])
            if entry-reports[i]["timestamp"]>=4*DAY: signals[entry]=dict(report_timestamp=reports[i]["timestamp"],net_share=current,median52=median,share_four_reports_ago=shares[i-4],open_interest=float(reports[i]["open_interest"]),asset_manager_long=float(reports[i]["asset_manager_long"]),asset_manager_short=float(reports[i]["asset_manager_short"]))
    check("signals_total",len(signals)==result["signals_total"])
    prices=[]
    for item in result["manifest"]:
        if item["kind"]!="binance_XRPUSDT_1d": continue
        doc=json.loads((cache/item["cache_file"]).read_bytes()); check("price_page_rows_"+item["cache_file"],len(doc)==item["rows"]); prices += [dict(timestamp=int(x[0]),open=float(x[1]),high=float(x[2]),low=float(x[3]),close=float(x[4])) for x in doc]
    check("price_rows",len(prices)==result["data_quality"]["price_rows"]); check("price_gaps",all(b["timestamp"]-a["timestamp"]==DAY for a,b in zip(prices,prices[1:]))); index={x["timestamp"]:i for i,x in enumerate(prices)}
    with gzip.open(dest/"trades.json.gz","rt") as h: ledgers=json.load(h)
    trade_checks=0
    for key,trades in ledgers.items():
        fee=.0019 if key.endswith("_stress") else .00095; slip=.0004 if key.endswith("_stress") else .0002; equities=[10_000.]
        for a,b in zip(trades,trades[1:]): check("nonoverlap_"+key+str(a["entry_timestamp"]),a["exit_timestamp"]<b["entry_timestamp"])
        for t in trades:
            trade_checks+=1; s=signals[t["entry_timestamp"]]; check("signal_"+str(trade_checks),all(close(t[k],v) if isinstance(v,float) else t[k]==v for k,v in s.items())); i=index[t["entry_timestamp"]]; row=prices[i]; check("lag_"+str(trade_checks),dt.datetime.fromtimestamp(t["entry_timestamp"]/1000,UTC).weekday()==0 and t["entry_timestamp"]-t["report_timestamp"]>=4*DAY)
            av=sum(max(prices[j]["high"]-prices[j]["low"],abs(prices[j]["high"]-prices[j-1]["close"]),abs(prices[j]["low"]-prices[j-1]["close"])) for j in range(i-14,i))/14
            check("entry_atr_"+str(trade_checks),close(t["raw_entry"],row["open"]) and close(t["entry"],row["open"]*(1+slip)) and close(t["atr"],av)); check("brackets_"+str(trade_checks),close(t["stop"],t["entry"]-2*av) and close(t["target"],t["entry"]+2.5*(t["entry"]-t["stop"]))); check("limits_"+str(trade_checks),t["leg_notional"]<=t["entry_equity"]*.2+1e-7 and t["qty"]*(t["entry"]-t["stop"])<=t["entry_equity"]*.005+1e-7)
            j=index[t["exit_timestamp"]]; erow=prices[j]; expected=erow["open"] if t["reason"]=="GAP_STOP" else t["stop"] if t["reason"]=="STOP" else t["target"] if t["reason"]=="TARGET" else erow["close"]; check("exit_"+str(trade_checks),close(t["raw_exit"],expected) and close(t["exit"],expected*(1-slip))); fees=t["qty"]*t["entry"]*fee+t["qty"]*t["exit"]*fee; pnl=t["qty"]*(t["exit"]-t["entry"])-fees; check("cost_"+str(trade_checks),close(t["fees"],fees) and close(t["pnl"],pnl) and close(t["equity"],t["entry_equity"]+pnl))
            entry_fee=t["qty"]*t["entry"]*fee; mark_end=j+1 if t["reason"]=="FOLD_END" else j
            for k in range(i,mark_end):
                mark=prices[k]["low"]*(1-slip); equities.append(t["entry_equity"]+t["qty"]*(mark-t["entry"])-entry_fee-t["qty"]*mark*fee)
            equities.append(t["equity"])
        metric=result["runs"][key]; wins=sum(max(0,x["pnl"]) for x in trades); losses=-sum(min(0,x["pnl"]) for x in trades); net=sum(x["pnl"] for x in trades); peak=10_000.; dd=0
        for e in equities: peak=max(peak,e); dd=max(dd,(peak-e)/peak*100)
        check("report_"+key,metric["trades"]==len(trades) and close(metric["net_pnl"],net) and close(metric["gross_profit"],wins) and close(metric["gross_loss"],losses) and close(metric["max_drawdown_pct"],dd) and (metric["profit_factor"] is None if not losses else close(metric["profit_factor"],wins/losses)))
    passed=all(x["passed"] for x in checks); result["gates"]["audit"]=passed; historical=all(v for k,v in result["gates"].items() if k!="forward_paper"); result["status"]="TEST NEDOKONCEN: forward PAPER required" if historical else "NEPROSEL"; (dest/"results.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n"); audit=dict(strategy=result["strategy"],passed=passed,checks=len(checks),trade_checks=trade_checks,failures=[x["name"] for x in checks if not x["passed"]]); (dest/"audit.json").write_text(json.dumps(audit,indent=2)+"\n"); print(audit,flush=True)
    if not passed: raise SystemExit(1)
if __name__=="__main__": main()
