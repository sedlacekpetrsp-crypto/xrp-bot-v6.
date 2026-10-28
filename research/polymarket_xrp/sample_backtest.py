"""Reproduce a small exploratory backtest, NOT a profitability certification.

python sample_backtest.py xrp_sample.parquet binance_sample.json
Research-only extra dependency: pandas and pyarrow.
Data: PolyOrderbooks, CC BY 4.0,
https://huggingface.co/datasets/polyorderbooks/polymarket-crypto-5min-l2
"""
import csv
import hashlib
import json
import sys
from pathlib import Path
import pandas as pd
from strategy import FIELDS, evaluate, backtest


def run(poly_path, binance_path, output):
    frame = pd.read_parquet(poly_path)
    bars = {int(x[0]) // 1000: x for x in json.loads(Path(binance_path).read_text())}
    rows, rejected = [], []
    for slug, group in frame.groupby('market_slug'):
        start = int(slug.rsplit('-', 1)[1])
        signal = start + 60
        group = group[(group.outcome == 'Up') & (group.coin == 'xrp')].copy()
        group['ts'] = group.captured_at.map(lambda x: x.timestamp())
        # Latest observation first; never fall back behind a newer invalid book.
        past = group[group.ts <= signal].sort_values('ts')
        if past.empty:
            rejected.append([slug, 'no observation']); continue
        q = past.iloc[-1]
        if signal-q.ts > 10 or q.crossed or not 0 < q.best_bid < q.best_ask < 1:
            rejected.append([slug, 'stale, missing, or crossed quote']); continue
        if q.market_end_at.timestamp() != start+300:
            rejected.append([slug, 'window mismatch']); continue
        if any(t not in bars for t in [start-60,start,start+120,start+300]):
            rejected.append([slug, 'missing Binance candle']); continue
        # Completed candles only; execute at next minute open after decision.
        rows.append(dict(window_start=start,window_end=start+300,
                         signal_ts=signal,poly_ts=float(q.ts),
                         binance_ts=bars[start][6]/1000,entry_ts=start+120,
                         exit_ts=start+300,p_up=(q.best_bid+q.best_ask)/2,
                         past_price=float(bars[start-60][4]),
                         signal_price=float(bars[start][4]),
                         entry_price=float(bars[start+120][1]),
                         exit_price=float(bars[start+300][1])))
    rows.sort(key=lambda r:r['window_start'])
    # Fix chronological split on all observed markets, before filtering.
    starts=sorted(int(s.rsplit('-',1)[1]) for s in frame.market_slug.unique())
    cutoff=starts[int(len(starts)*.7)]
    report=evaluate(rows,cutoff)
    report.update(source='PolyOrderbooks, CC BY 4.0',
                  source_url='https://huggingface.co/datasets/polyorderbooks/polymarket-crypto-5min-l2',
                  source_sha256=hashlib.sha256(Path(poly_path).read_bytes()).hexdigest(),
                  binance_sha256=hashlib.sha256(Path(binance_path).read_bytes()).hexdigest(),
                  snapshot_count=len(frame),market_count=len(starts),
                  accepted_windows=len(rows),rejected=rejected,
                  execution='Binance 1m open at start+120s; exit at start+300s; modeled fills, no depth',
                  limitation='Single few-hour sample, third-party snapshot accuracy unaudited; no reliable edge verdict')
    train=[r for r in rows if r['exit_ts']<cutoff]
    test=[r for r in rows if r['window_start']>=cutoff]
    report['training']=backtest(train,report['threshold'],10,5)
    report['out_of_sample_zero_costs']=backtest(test,report['threshold'],0,0)
    baseline=[dict(r,p_up=.999) for r in test]
    report['out_of_sample_momentum_only']=backtest(baseline,.5,10,5)
    report['all_sample_at_selected_threshold_in_sample_biased']=backtest(rows,report['threshold'],10,5)
    output=Path(output)
    output.mkdir(exist_ok=True)
    with (output/'sample_aligned.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader();writer.writerows(rows)
    (output/'sample_results.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    run(sys.argv[1],sys.argv[2],Path(__file__).parent)
