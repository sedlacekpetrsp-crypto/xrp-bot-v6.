# FIB timeframe screening — 20 October 2026

Decision: no production filter/timeframe change. PAPER v13 remains deployed. Paused strategies remain paused.

## Results

All figures are simulated USDC after fees/slippage. Independent 10,000 USDC starting account for each period, cash risk capped near 9.18 USDC per trade.

| Variant | Apr–Jun trades | Apr–Jun net | Jul–Sep trades | Jul–Sep net | Jul–Sep double-slip net |
|---|---:|---:|---:|---:|---:|
| Current 5m | 2 | 6.41 | 1 | -9.18 | -9.18 |
| 15m candidate | 10 | -28.28 | 11 | -64.25 | -45.89 |
| 1h exploratory | 2 | -18.36 | 4 | -1.50 | -2.72 |

The preregistered 15m screening gate failed. The 1h extension was added after seeing the 15m result and reuses the date windows; it is exploratory, not independent confirmation. No result establishes future profitability.

## Method and limits

- 246,528 five-minute bars across BTC/ETH/SOL/XRP, March–September 2026. March is warmup; evaluation is April–September. Monthly ZIP SHA-256 values checked against Binance CHECKSUM files; derived dataset hashes retained.
- Production FIB candidate, multi-timeframe confirmation (score 4 and 1h veto), entry sizing, cash caps and fee arithmetic reused from c111da1. Only the FIB signal timeframe changes.
- Fee 0.095% per side, slippage 0.02% per side; stress uses 0.04% slippage per side. Stop multiplier 1.15. Two-position maximum and original stop/target restrictions retained.
- No future candles: closed input only, next 5m open entry, gap-aware stop; stop wins if stop and target both touched in one bar. Breakeven moves only after bar close.
- FIB-only approximation, not the full production portfolio: no VWAP/4h interactions, no historical news veto, no 10-second exit path, no minute-by-minute entry retry. Intrabar ordering is not observable.
- 1e-8 USDC tolerance classifies floating-point breakevens; raw trade values are retained.

## Verification

Five simulator tests passed: aggregation close timing, future-bar isolation, gap rejection, stop-first ordering/next-open entry and worse-price gap fill. Sixteen production regression tests passed for stop-risk sizing, execution freshness and paused reversion.

## Reproduce

```sh
python -m pip install -r requirements.txt
python research/fib_timeframe_20261020/download.py /tmp/fib-data
python research/fib_timeframe_20261020/test_replay.py
python research/fib_timeframe_20261020/run.py /tmp/fib-data
python research/fib_timeframe_20261020/extension.py /tmp/fib-data
python research/fib_timeframe_20261020/summarize.py
```

Signals and simulated fills are research output only. No live orders or database writes are performed.
