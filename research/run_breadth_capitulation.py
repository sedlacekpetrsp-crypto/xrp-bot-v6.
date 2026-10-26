"""Download fixed multi-market spot basket and run frozen OOS screen."""
import concurrent.futures
import csv
import gzip
import hashlib
import io
import json
import pathlib
import sys
import urllib.request
import zipfile
from dataclasses import replace

from research.breadth_capitulation_v1 import Config, STEP, backtest, validate_series
from research.run_autocorr_history import metrics as score, stamp

SYMBOLS = ("XRPUSDT", "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "DOGEUSDT", "LINKUSDT", "LTCUSDT")
BASKET = SYMBOLS[1:]
MONTHS = [(y, m) for y in range(2022, 2027) for m in range(1, 13) if (y, m) < (2026, 10)]


def fetch(job):
    symbol, y, m, cache = job
    name = f"{symbol}-1h-{y}-{m:02d}.zip"
    url = f"https://data.binance.vision/data/spot/monthly/klines/{symbol}/1h/{name}"
    path = cache/name
    if not path.exists():
        with urllib.request.urlopen(url, timeout=45) as response:
            path.write_bytes(response.read())
    payload = path.read_bytes()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        members = archive.namelist()
        if members != [name[:-4]+".csv"]:
            raise ValueError("unexpected archive members")
        rows = list(csv.reader(io.TextIOWrapper(archive.open(members[0]))))
    bars = []
    for row in rows:
        timestamp = int(row[0]); timestamp = timestamp//1000 if timestamp > 10**14 else timestamp
        bars.append(dict(timestamp=timestamp, open=float(row[1]), high=float(row[2]), low=float(row[3]), close=float(row[4])))
    validate_series(bars)
    return symbol, bars, dict(symbol=symbol, url=url, sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload), rows=len(bars))


def folds():
    output=[("2022_control",stamp(2022,1),stamp(2023,1))]
    for year in range(2023,2027):
        for quarter,month in enumerate((1,4,7,10),1):
            if (year,month)>=(2026,10): continue
            ey,em=(year+1,1) if month==10 else (year,month+3)
            output.append((f"{year}Q{quarter}",stamp(year,month),stamp(ey,em)))
    output.append(("continuous_oos",stamp(2023,1),stamp(2026,10)))
    return output


def aggregate(trades):
    wins=sum(max(0,t["pnl"]) for t in trades); losses=-sum(min(0,t["pnl"]) for t in trades)
    return dict(trades=len(trades),net_pnl=wins-losses,profit_factor=wins/losses if losses else None,expectancy=(wins-losses)/len(trades) if trades else None)


def main():
    cache=pathlib.Path(sys.argv[1]); cache.mkdir(parents=True,exist_ok=True)
    destination=pathlib.Path(sys.argv[2]); destination.mkdir(parents=True,exist_ok=True)
    jobs=[(symbol,y,m,cache) for symbol in SYMBOLS for y,m in MONTHS]
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        chunks=list(pool.map(fetch,jobs))
    grouped={symbol:[] for symbol in SYMBOLS}; manifest=[]
    for symbol,bars,source in chunks:
        grouped[symbol].extend(bars); manifest.append(source)
    quality={}
    for symbol,bars in grouped.items():
        raw_count=len(bars); mapping={bar["timestamp"]:bar for bar in bars}; grouped[symbol]=[mapping[t] for t in sorted(mapping)]
        quality[symbol]=dict(duplicates=raw_count-len(mapping),gaps=[(a["timestamp"],b["timestamp"],(b["timestamp"]-a["timestamp"])//STEP-1) for a,b in zip(grouped[symbol],grouped[symbol][1:]) if b["timestamp"]-a["timestamp"]!=STEP])
    xrp=grouped["XRPUSDT"]; basket={symbol:grouped[symbol] for symbol in BASKET}; runs={}; ledger={}
    for name,start,end in folds():
        for cost,multiplier in (("base",1),("stress",2)):
            config=replace(Config(),fee=Config().fee*multiplier,slippage=Config().slippage*multiplier)
            trades=backtest(xrp,basket,start,end,config); key=f"{name}_{cost}"
            runs[key]=score(xrp,trades,10_000,config); runs[key]["slippage_cost"]=sum(t["slippage_cost"] for t in trades)
            ledger[key]=[dict(t,signal_timestamp=xrp[t["signal_index"]]["timestamp"],entry_timestamp=xrp[t["entry_index"]]["timestamp"],exit_timestamp=xrp[t["exit_index"]]["timestamp"]) for t in trades]
            print(key,runs[key],flush=True)
    quarters=[name for name,_,_ in folds() if name not in ("2022_control","continuous_oos")]
    base_trades=[t for q in quarters for t in ledger[f"{q}_base"]]; stress_trades=[t for q in quarters for t in ledger[f"{q}_stress"]]
    base,stress=aggregate(base_trades),aggregate(stress_trades); by_quarter={q:runs[f"{q}_base"]["net_pnl"] for q in quarters}
    positive_total=sum(max(0,value) for value in by_quarter.values())
    gates=dict(sample=base["trades"]>=150,base_net=base["net_pnl"]>0,base_expectancy=(base["expectancy"] or 0)>0,base_pf=(base["profit_factor"] or 0)>1.15,stress_net=stress["net_pnl"]>0,stress_expectancy=(stress["expectancy"] or 0)>0,stress_pf=(stress["profit_factor"] or 0)>1.02,ten_positive_quarters=sum(value>0 for value in by_quarter.values())>=10,final_quarter=by_quarter["2026Q3"]>0,drawdown=all(runs[f"continuous_oos_{cost}"]["max_drawdown_pct"]<=10 for cost in ("base","stress")),concentration=base["net_pnl"]>0 and positive_total>0 and max(by_quarter.values())<=.30*positive_total)
    protocol=pathlib.Path("research/breadth_capitulation_protocol.md")
    result=dict(strategy="ALT_BREADTH_CAPITULATION_REVERSAL_V1",status="NEPROSEL" if not all(gates.values()) else "TEST NEDOKONCEN: forward evidence required",protocol=str(protocol),protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),manifest=manifest,data_quality=quality,runs=runs,aggregate_oos=base,aggregate_stress=stress,by_quarter=by_quarter,gates=gates,limitations=["Exploratory historical evidence.","Local SHA256 are not publisher signatures.","Basket membership was fixed before evaluation.","No independent forward PAPER evidence."])
    (destination/"results.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    with gzip.open(destination/"trades.json.gz","wt") as handle: json.dump(ledger,handle)
    print(result["status"],gates)


if __name__=="__main__": main()
