"""POLYMARKET_XRP_SIGNAL_V1: offline PAPER hypothesis, no order API.

Trade Binance XRPUSDT spot long for the remaining 5-minute market window
when pre-entry Polymarket Up probability >= threshold and past Binance
momentum is positive. This does NOT trade or settle Polymarket contracts.
CSV timestamps are UTC Unix seconds. See README for the data contract.
"""
import argparse
import csv
import json
import math

NAME = 'POLYMARKET_XRP_SIGNAL_V1'
FIELDS = ('window_start', 'window_end', 'signal_ts', 'poly_ts',
          'binance_ts', 'entry_ts', 'exit_ts', 'p_up', 'past_price',
          'signal_price', 'entry_price', 'exit_price')


def validate(rows):
    previous_end = -math.inf
    for r in rows:
        if any(not math.isfinite(r[k]) for k in FIELDS):
            raise ValueError('Nonfinite or missing input')
        s, e, t = r['window_start'], r['window_end'], r['signal_ts']
        if e - s != 300 or s < previous_end:
            raise ValueError('Require chronological nonoverlapping 5-minute windows')
        if not s <= r['poly_ts'] <= t < r['entry_ts'] < e <= r['exit_ts'] <= e + 5:
            raise ValueError('Future/stale Polymarket signal or invalid execution time')
        if t - r['poly_ts'] > 60 or not t - 60 <= r['binance_ts'] <= t:
            raise ValueError('Stale or future market data')
        if not 0 < r['p_up'] < 1:
            raise ValueError('Exclude settlement probabilities')
        if min(r[k] for k in ('past_price','signal_price','entry_price','exit_price')) <= 0:
            raise ValueError('Prices must be positive')
        previous_end = r['exit_ts']


def backtest(rows, threshold, fee_bps, slippage_bps):
    validate(rows)
    if not .5 <= threshold < 1 or not 0 <= fee_bps < 10000 or not 0 <= slippage_bps < 10000:
        raise ValueError('Invalid threshold or cost assumption')
    equity = peak = 1.0
    drawdown = 0.0
    trades = []
    fee, slip = fee_bps / 10000, slippage_bps / 10000
    for r in rows:
        if r['p_up'] < threshold or r['signal_price'] <= r['past_price']:
            continue
        factor = r['exit_price'] * (1-slip) * (1-fee) / (r['entry_price'] * (1+slip) * (1+fee))
        equity *= factor
        peak = max(peak, equity)
        drawdown = max(drawdown, 1-equity/peak)
        trades.append({'entry_ts':r['entry_ts'], 'exit_ts':r['exit_ts'], 'net_return':factor-1})
    return {'net_return':equity-1, 'max_closed_trade_drawdown':drawdown,
            'trade_count':len(trades), 'trades':trades}


def evaluate(rows, cutoff, fee_bps=10, slippage_bps=5):
    validate(rows)
    train = [r for r in rows if r['exit_ts'] < cutoff]
    test = [r for r in rows if r['window_start'] >= cutoff]
    if not train or not test:
        return {'verdict':'TEST NEDOKONČEN', 'reason':'Missing chronological train/test data',
                'net_return':None, 'max_drawdown':None, 'trade_count':0}
    grid = (.55, .60, .65, .70)
    threshold = max(grid, key=lambda p:backtest(train,p,fee_bps,slippage_bps)['net_return'])
    out = backtest(test,threshold,fee_bps,slippage_bps)
    stress = backtest(test,threshold,fee_bps*2,slippage_bps*2)
    # Positive PnL alone is not evidence of a statistically reliable edge.
    return {'strategy':NAME, 'mode':'PAPER', 'verdict':'TEST NEDOKONČEN',
            'reason':'Exploratory result; requires provenance audit, sufficient sample and independent forward test',
            'threshold':threshold, 'cutoff':cutoff, 'fee_bps_per_side':fee_bps,
            'slippage_bps_per_side':slippage_bps, 'train_rows':len(train),
            'test_rows':len(test), 'out_of_sample':out, 'double_costs':stress}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv')
    parser.add_argument('--cutoff', type=float, required=True)
    parser.add_argument('--fee-bps', type=float, default=10)
    parser.add_argument('--slippage-bps', type=float, default=5)
    args = parser.parse_args()
    with open(args.csv, newline='') as f:
        rows = [{k:float(r[k]) for k in FIELDS} for r in csv.DictReader(f)]
    print(json.dumps(evaluate(rows,args.cutoff,args.fee_bps,args.slippage_bps),indent=2))
