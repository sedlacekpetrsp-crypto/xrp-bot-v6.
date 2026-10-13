"""ELITE V1 — isolated research runner, no trading credentials or orders.

Usage:
  python -m elite.run_csv --csv xrp_5m.csv --output elite_report.json
CSV columns: timestamp_ms,open,high,low,close (chronological).
"""
import argparse
import csv
import json
from elite.backtest import backtest

def read_csv(path):
    rows=[]
    with open(path,newline="") as f:
        for r in csv.DictReader(f):
            ts=int(r["timestamp_ms"])
            o,h,l,c=[float(r[k]) for k in ("open","high","low","close")]
            if not (0<l<=min(o,c)<=max(o,c)<=h):
                raise ValueError(f"Invalid OHLC at {ts}")
            rows.append((ts,(o,h,l,c)))
    if len(rows)<1000:
        raise ValueError("At least 1000 five-minute candles required")
    for (t1,_),(t2,_) in zip(rows,rows[1:]):
        if t2-t1!=300000:
            raise ValueError(f"Missing or duplicate candle between {t1} and {t2}")
    return rows

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--csv",required=True)
    parser.add_argument("--output",default="elite_report.json")
    args=parser.parse_args()
    rows=read_csv(args.csv)
    bars=[r[1] for r in rows]
    cut1=int(len(bars)*.6)
    cut2=int(len(bars)*.8)
    result={"warning":"Research-only simulated results. No live performance evidence.",
            "periods":{}}
    for label,lo,hi in (("development",0,cut1),
                        ("validation",cut1,cut2),
                        ("holdout",cut2,len(bars))):
        warm=max(0,lo-101)
        segment=bars[warm:hi]
        # Warmup 101 bars. The backtest starts on bar 99, so discard
        # any warmup trades from later periods and report filtered ledger.
        run=backtest(segment)
        trades=[t for t in run["trade_log"] if t.entry_index+warm>=lo]
        wins=sum(t.pnl>0 for t in trades)
        gp=sum(max(t.pnl,0) for t in trades)
        gl=-sum(min(t.pnl,0) for t in trades)
        equity=10000.0; peak=equity; dd=0.0
        for t in trades:
            equity+=t.pnl
            peak=max(peak,equity)
            dd=max(dd,(peak-equity)/peak)
        result["periods"][label]={
            "bars":hi-lo,"trades":len(trades),
            "net_pnl":round(sum(t.pnl for t in trades),2),
            "win_rate":round(wins/len(trades),4) if trades else None,
            "profit_factor":round(gp/gl,4) if gl else None,
            "max_drawdown_pct":round(dd*100,3),
            "first_timestamp_ms":rows[lo][0],
            "last_timestamp_ms":rows[hi-1][0]}
    with open(args.output,"w") as f:
        json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))

if __name__=="__main__":main()
