"""ELITE research evaluation: fixed chronological splits, no parameter fitting.

Run: python -m elite.evaluate --start 2025-10 --end 2026-09
Results are research-only, not evidence of live execution.
"""
import argparse
import json
from dataclasses import asdict
from elite.data_loader import load
from elite.backtest import backtest

def evaluate(rows, strategy='v1'):
    if len(rows)<1200:
        raise ValueError("insufficient candles for chronological evaluation")
    n=len(rows)
    cuts=[0,int(n*0.6),int(n*0.8),n]
    labels=["development","validation","holdout"]
    result={"strategy":strategy,"total_bars":n,"periods":{}}
    for j,label in enumerate(labels):
        start,end=cuts[j],cuts[j+1]
        # Exactly 101 prior candles for indicator warmup; results only
        # counted if entry occurs within the target period.
        offset=max(0,start-101)
        warm=rows[offset:end]
        candles=[tuple(r[1:5]) for r in warm]
        summary=backtest(candles,strategy=strategy)
        # For the first period, all entries are in-period. For later periods,
        # warmup length is 101 and first entry occurs at index 100 or later.
        trades=[t for t in summary["trade_log"] if t.entry_index+offset>=start]
        # Avoid pretending that a warmup-initiated trade is in-sample.
        # Compute segment metrics from the filtered trade ledger.
        pnl=sum(t.pnl for t in trades)
        wins=sum(t.pnl>0 for t in trades)
        gp=sum(max(t.pnl,0) for t in trades)
        gl=-sum(min(t.pnl,0) for t in trades)
        equity=10000.0
        peak=equity
        dd=0.0
        for t in trades:
            equity+=t.pnl
            peak=max(peak,equity)
            dd=max(dd,(peak-equity)/peak)
        result["periods"][label]={
            "bars":end-start,"trades":len(trades),"net_pnl":round(pnl,2),
            "win_rate":round(wins/len(trades),4) if trades else None,
            "profit_factor":round(gp/gl,4) if gl else None,
            "max_drawdown_pct":round(dd*100,3),
            "first_timestamp_ms":rows[start][0],
            "last_timestamp_ms":rows[end-1][0],
        }
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--start",default="2025-10")
    parser.add_argument("--end",default="2026-09")
    parser.add_argument("--output",default="elite-results.json")
    parser.add_argument("--strategy",choices=["v1","v2","v3","v4"],default="v1")
    args=parser.parse_args()
    report=evaluate(load(args.start,args.end),strategy=args.strategy)
    with open(args.output,"w") as f:
        json.dump(report,f,indent=2)
    print(json.dumps(report,indent=2))

if __name__=="__main__":main()
