"""Run preregistered historical study. Requires public network; no trading credentials."""
import csv,gzip,hashlib,io,json,urllib.request,zipfile
from pathlib import Path
from datetime import datetime,timezone
from calendar import monthrange
from research.cross_market_dispersion_20261026.strategy import ASSETS,Config,backtest,validate

ROOT=Path("research/cross_market_dispersion_20261026")
MONTHS=[(y,m) for y in range(2022,2027) for m in range(1,13) if (y,m)<=(2026,9)]
HOUR=3600000

def download(symbol):
    rows=[];provenance=[]
    for y,m in MONTHS:
        name=f"{symbol}-1h-{y}-{m:02d}.zip"
        url=f"https://data.binance.vision/data/spot/monthly/klines/{symbol}/1h/{name}"
        with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"research-dispersion/1.0"}),timeout=120) as resp:
            data=resp.read()
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
        if count!=(end-start)//HOUR:raise ValueError(f"missing bars {name}: {count}")
        provenance.append(dict(url=url,sha256=sha,bars=count))
    return rows,provenance

def metrics(trades):
    wins=sum(max(0,t["pnl"]) for t in trades)
    losses=-sum(min(0,t["pnl"]) for t in trades)
    return dict(count=len(trades),net_pnl=sum(t["pnl"] for t in trades),profit_factor=wins/losses if losses else None)

def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    markets={};sources={}
    for a in ASSETS:markets[a],sources[a]=download(a)
    validate(markets)
    # Preserve OOS boundary; earlier history is only used as indicator warmup.
    out={"sources":sources,"results":{},"protocol":"fixed 2026-10-26; all observations exploratory"}
    for stress in (False,True):
        trades=backtest(markets,Config(),stress)
        key="stress" if stress else "base"
        with gzip.open(ROOT/f"trades_{key}.json.gz","wt") as f:json.dump(trades,f)
        out["results"][key]={"all":metrics(trades),"2025":metrics([t for t in trades if 2025==datetime.fromtimestamp(markets[ASSETS[0]][t["entry_index"]]["timestamp"]/1000,timezone.utc).year]),"2026":metrics([t for t in trades if 2026==datetime.fromtimestamp(markets[ASSETS[0]][t["entry_index"]]["timestamp"]/1000,timezone.utc).year])}
    (ROOT/"results.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out["results"],indent=2))

if __name__=="__main__":main()
