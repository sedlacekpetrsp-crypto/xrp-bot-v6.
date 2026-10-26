"""Run preregistered historical study. Requires public network; no trading credentials."""
import csv,gzip,hashlib,io,json,urllib.request,zipfile,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from datetime import datetime,timezone
from calendar import monthrange
from research.cross_market_dispersion_20261026.strategy import ASSETS,Config,backtest,validate

ROOT=Path("research/cross_market_dispersion_20261026")
MONTHS=[(y,m) for y in range(2022,2027) for m in range(1,13) if (y,m)<=(2026,9)]
HOUR=3600000

def fetch(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url,timeout=45) as resp: return resp.read()
        except Exception:
            if attempt==2: raise
            time.sleep(attempt+1)

def download(symbol, months=MONTHS):
    rows=[];provenance=[]
    for y,m in months:
        name=f"{symbol}-1h-{y}-{m:02d}.zip"
        url=f"https://data.binance.vision/data/spot/monthly/klines/{symbol}/1h/{name}"
        cache=Path("/tmp/dispersion-archives")/name
        cache.parent.mkdir(exist_ok=True)
        data=cache.read_bytes() if cache.exists() else fetch(url)
        checksum=fetch(url+".CHECKSUM").decode().split()[0]
        if hashlib.sha256(data).hexdigest()!=checksum: raise ValueError(f"Checksum mismatch: {name}")
        cache.write_bytes(data)
        sha=hashlib.sha256(data).hexdigest()
        start=int(datetime(y,m,1,tzinfo=timezone.utc).timestamp()*1000)
        end=int(datetime(y+1,1,1,tzinfo=timezone.utc).timestamp()*1000) if m==12 else int(datetime(y,m+1,1,tzinfo=timezone.utc).timestamp()*1000)
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names=[x for x in z.namelist() if x.endswith(".csv")]
            if len(names)!=1:raise ValueError(name)
            parsed=list(csv.reader(io.TextIOWrapper(z.open(names[0]))))
        count=0
        for r in parsed:
            if not r or not r[0].isdigit():continue
            ts=int(r[0]);ts=ts//1000 if ts>10**14 else ts
            if not start<=ts<end:raise ValueError(f"out of month {name}")
            rows.append(dict(timestamp=ts,open=float(r[1]),high=float(r[2]),low=float(r[3]),close=float(r[4])))
            count+=1
        expected=(end-start)//HOUR
        provenance.append(dict(url=url,sha256=sha,checksum_url=url+".CHECKSUM",checksum_verified=True,bars=count,expected_bars=expected))
    return rows,provenance

def metrics(trades):
    wins=sum(max(0,t["pnl"]) for t in trades)
    losses=-sum(min(0,t["pnl"]) for t in trades)
    start=trades[0]["equity_before"] if trades else 10000
    monthly={}
    for t in trades:
        month=datetime.fromtimestamp(t["entry_timestamp"]/1000,timezone.utc).strftime("%Y-%m")
        monthly[month]=monthly.get(month,0)+t["pnl"]
    net=sum(t["pnl"] for t in trades)
    return dict(count=len(trades),net_pnl=net,return_pct=100*net/start,
                profit_factor=wins/losses if losses else None,
                max_drawdown_bound_pct=100*max((t["drawdown_bound"] for t in trades),default=0),
                monthly_pnl=monthly,max_month_share_of_net=max(monthly.values(),default=0)/net if net>0 else None)

def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    markets={};sources={}
    tasks=[(a,month) for a in ASSETS for month in MONTHS]
    markets={a:[] for a in ASSETS};sources={a:[] for a in ASSETS}
    with ThreadPoolExecutor(max_workers=12) as pool:
        for (a,month),(rows,provenance) in zip(tasks,pool.map(lambda task:download(task[0],[task[1]]),tasks)):
            markets[a].extend(rows);sources[a].extend(provenance)
            print(f"Verified {a} {month}",flush=True)
    # Never fabricate missing exchange candles. Split timestamp intersection into
    # contiguous blocks; each block needs a fresh 180-day warmup. This diagnostic
    # does not replace the frozen strict full-coverage acceptance gate.
    maps={a:{r["timestamp"]:r for r in rows} for a,rows in markets.items()}
    if any(len(maps[a])!=len(markets[a]) for a in ASSETS): raise ValueError("Duplicate timestamps")
    times=sorted(set.intersection(*(set(v) for v in maps.values())))
    blocks=[];start=0
    for i in range(1,len(times)):
        if times[i]-times[i-1]!=HOUR: blocks.append(times[start:i]);start=i
    blocks.append(times[start:])
    segments=[{a:[maps[a][t] for t in block] for a in ASSETS} for block in blocks]
    for segment in segments: validate(segment)
    gaps=[dict(before=times[i-1],after=times[i],missing_hours=(times[i]-times[i-1])//HOUR-1) for i in range(1,len(times)) if times[i]-times[i-1]!=HOUR]
    # Preserve OOS boundary; earlier history is only used as indicator warmup.
    out={"sources":sources,"results":{},"protocol":"fixed 2026-10-26; all observations exploratory"}
    out["data_audit"]={"gaps":gaps,"aligned_bars":len(times),"segments":[{"start":b[0],"end":b[-1],"bars":len(b)} for b in blocks],"strict_coverage_pass":not gaps and all(p["bars"]==p["expected_bars"] for pp in sources.values() for p in pp)}
    for stress in (False,True):
        trades=[];capital=10000;peak=10000
        for segment_id,segment in enumerate(segments):
            part=backtest(segment,Config(),stress,initial=capital,initial_peak=peak)
            for t in part:t["segment_id"]=segment_id
            trades.extend(part)
            if part:capital=part[-1]["equity"];peak=part[-1]["peak_equity"]
        key="stress" if stress else "base"
        with gzip.open(ROOT/f"trades_{key}.json.gz","wt") as f:json.dump(trades,f)
        year=lambda t: datetime.fromtimestamp(t["entry_timestamp"]/1000,timezone.utc).year
        out["results"][key]={"all":metrics(trades),"2022":metrics([t for t in trades if year(t)==2022]),
            "development":metrics([t for t in trades if 2023<=year(t)<=2024]),
            "oos":metrics([t for t in trades if year(t)>=2025]),
            "2025":metrics([t for t in trades if year(t)==2025]),"2026":metrics([t for t in trades if year(t)==2026])}
    base=out["results"]["base"];stress=out["results"]["stress"]
    gates={"oos_count":base["oos"]["count"]>=100,
           "oos_pf":(base["oos"]["profit_factor"] or 0)>=1.2,
           "oos_stress_pf":(stress["oos"]["profit_factor"] or 0)>1.05,
           "positive_years":all(r[y]["net_pnl"]>0 for r in (base,stress) for y in ("2025","2026")),
           "drawdown":all(r["all"]["max_drawdown_bound_pct"]<=10 for r in (base,stress)),
           "concentration":base["oos"]["max_month_share_of_net"] is not None and base["oos"]["max_month_share_of_net"]<=.5}
    gates["strict_data_coverage"]=out["data_audit"]["strict_coverage_pass"]
    out["historical_gates"]=gates
    out["decision"]="HISTORICAL_PASS_FORWARD_REQUIRED" if all(gates.values()) else "NEPROSEL"
    out["evaluation_mode"]="strict" if gates["strict_data_coverage"] else "contiguous-block diagnostic; frozen full-coverage gate failed"
    out["limitations"]=["Synthetic spot shorts; borrow availability unverified", "Intrabar paired stop uses adverse price bound, not exact fills", "Drawdown is a conservative simultaneous-extremes bound", "Previously examined history; no untouched holdout or forward evidence"]
    (ROOT/"results.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out["results"],indent=2))

if __name__=="__main__":main()
