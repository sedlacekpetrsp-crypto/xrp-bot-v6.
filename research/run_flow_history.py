"""Reproducible XRP 15m research; monthly spot archives, no trading APIs."""
import csv
import hashlib
import io
import json
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from research.flow_pressure_v1 import Config, backtest
from research.fetch_binance_klines import MONTHS


def fetch(month):
    year, number = month
    filename = f'XRPUSDT-15m-{year}-{number:02d}.zip'
    url = 'https://data.binance.vision/data/spot/monthly/klines/XRPUSDT/15m/'+filename
    with urllib.request.urlopen(url, timeout=45) as r:
        payload = r.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        records = list(csv.reader(io.TextIOWrapper(z.open(filename.replace('.zip', '.csv')))))
    bars = []
    for row in records:
        ts = int(row[0])
        if ts > 10**14:
            ts //= 1000
        bar = dict(zip(('open','high','low','close','volume'), map(float, row[1:6])))
        bar.update(timestamp=ts, taker_buy_base=float(row[9]))
        bars.append(bar)
    start = int(datetime(year,number,1,tzinfo=timezone.utc).timestamp()*1000)
    end = int(datetime(year+int(number==12),number%12+1,1,tzinfo=timezone.utc).timestamp()*1000)
    assert [b['timestamp'] for b in bars] == list(range(start,end,900000)), filename
    return bars, dict(url=url, sha256=hashlib.sha256(payload).hexdigest(), bars=len(bars))


def metrics(trades):
    wins = sum(max(0,t['net_return']) for t in trades)
    losses = -sum(min(0,t['net_return']) for t in trades)
    return dict(trades=len(trades), win_rate=sum(t['net_return']>0 for t in trades)/len(trades) if trades else None,
                profit_factor=wins/losses if losses else None,
                mean_net_bps=10000*sum(t['net_return'] for t in trades)/len(trades) if trades else None)


def main():
    with ThreadPoolExecutor(max_workers=4) as pool:
        parts = list(pool.map(fetch, MONTHS))
    bars = [b for part,_ in parts for b in part]
    assert all(bars[i]['timestamp']-bars[i-1]['timestamp']==900000 for i in range(1,len(bars)))
    # Fixed calendar split: first nine months / final three months.
    cutoff = int(datetime(2026,7,1,tzinfo=timezone.utc).timestamp()*1000)
    train = [b for b in bars if b['timestamp']<cutoff]
    test = [b for b in bars if b['timestamp']>=cutoff]
    c = Config()
    report = dict(strategy='FLOW_PRESSURE_V1', symbol='XRPUSDT', interval='15m',
                  period='2025-10-01/2026-09-30', test_period='2026-07-01/2026-09-30',
                  config=c.__dict__, candles=len(bars), manifest=[m for _,m in parts],
                  train=metrics(backtest(train,c)), test=metrics(backtest(test,c)),
                  test_double_costs=metrics(backtest(test,replace(c, fee=c.fee*2,slippage=c.slippage*2))),
                  limitation='One market; OHLC simulation, approximate close-weighted VWAP, no portfolio sizing. Previously viewed period; not an untouched final holdout. No deployment authorization.')
    Path('research/flow_pressure_results_20261020.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='manifest'},indent=2))


if __name__ == '__main__':
    main()
