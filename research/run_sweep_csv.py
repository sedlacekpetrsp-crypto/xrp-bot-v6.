"""Offline CSV backtest runner for SWEEP_TREND_V1, no trading connections.

Usage: python -m research.run_sweep_csv path/to/closed_ohlcv.csv
CSV columns: timestamp,open,high,low,close,volume
"""
import csv
import json
import sys
from research.sweep_trend_v1 import backtest, Config

def metrics(trades):
    n = len(trades)
    wins = [t["net_return"] for t in trades if t["net_return"] > 0]
    losses = [t["net_return"] for t in trades if t["net_return"] <= 0]
    equity = peak = 1.0
    drawdown = 0.0
    for trade in trades:
        equity *= 1 + trade["net_return"]
        peak = max(peak, equity)
        drawdown = max(drawdown, 1 - equity / peak)
    return {"trades":n,"win_rate":len(wins)/n if n else None,
            "profit_factor":sum(wins)/abs(sum(losses)) if losses else None,
            "compounded_return":equity-1,"max_drawdown":drawdown}

def run(path):
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        required = {"timestamp","open","high","low","close","volume"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Missing OHLCV CSV columns")
        rows = list(reader)
    if len(rows) < 500:
        raise ValueError("At least 500 closed candles required")
    times = [r["timestamp"] for r in rows]
    if len(set(times)) != len(times) or times != sorted(times):
        raise ValueError("Timestamps must be unique and increasing ISO-8601")
    bars = []
    for row in rows:
        b = {key:float(row[key]) for key in ("open","high","low","close","volume")}
        if min(b["open"],b["high"],b["low"],b["close"]) <= 0 or b["volume"] < 0 or b["high"] < max(b["open"],b["close"]) or b["low"] > min(b["open"],b["close"]):
            raise ValueError("Invalid OHLCV bar")
        bars.append(b)
    cutoff = int(len(bars)*0.7)
    report = {"source":path,"candles":len(bars),"train":metrics(backtest(bars[:cutoff],Config())),
              "test":metrics(backtest(bars[cutoff:],Config())),"warning":"Research only; no live or PAPER orders"}
    return report

if __name__ == "__main__":
    print(json.dumps(run(sys.argv[1]),indent=2))
