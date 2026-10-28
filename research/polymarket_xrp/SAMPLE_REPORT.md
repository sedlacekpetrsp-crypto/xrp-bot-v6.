# First real-data pilot — 2026-10-28

This supersedes the earlier no-data status in README, results.json and search notes.
Verdict: TEST NEDOKONČEN for reliable edge assessment. Pilot is unprofitable.

Downloaded actual XRP order-book snapshots without registration from PolyOrderbooks:
https://huggingface.co/datasets/polyorderbooks/polymarket-crypto-5min-l2/resolve/main/xrp.parquet
Attribution: PolyOrderbooks, CC BY 4.0. Derived aligned observations retain this attribution.
SHA256: 999135bafbc9371e1d9ff4a255e815b707b60359279476420f23c778f397bb05
File: 998,022 bytes; 23,478 rows; 44 XRP markets on 2026-08-23.
Observed snapshots run 09:04:02–12:44:59 UTC, including pre-window observations.

Binance XRPUSDT minute data downloaded from:
https://data-api.binance.vision/api/v3/klines?symbol=XRPUSDT&interval=1m&startTime=1787475840000&endTime=1787489640000&limit=1000
231 candles, SHA256 in sample_results.json. No account-specific fees verified.

Method: sample Up midpoint at window start+60 seconds from the latest snapshot,
maximum age 10 seconds. Exclude crossed/one-sided quotes and mismatched windows.
All 44 windows had eligible observations. Positive momentum uses two completed
Binance one-minute candle closes. Buy at start+120s minute open, exit at start+300s
minute open. These are modeled fills, not recorded executable Binance bid/asks.
No Polymarket orders or settlement PnL; only the pre-entry Up quote is a signal.
Final outcome columns are never used as features.

Split before filtering: first 70% of market starts determine training cutoff.
29 training windows, one boundary window purged, 14 test windows. Four threshold
candidates tried on training only; 0.70 selected. Selection is not statistical proof.
Fee 10 bps and slippage 5 bps per side; full equity allocated per simulated trade.

| Segment/scenario | Trades | Net return | Closed-trade max drawdown |
|---|---:|---:|---:|
| Training | 6 | -1.7419% | 1.8211% |
| Chronological holdout | 5 | -1.7003% | 1.7003% |
| Holdout, zero costs | 5 | -0.2147% | 0.4942% |
| Holdout, double costs | 5 | -3.1638% | 3.1638% |
| Holdout, momentum-only baseline | 8 | -2.7370% | 2.7370% |

Full sample using the training-selected threshold: 11 trades, -3.4127%, closed-trade
drawdown 3.4127%; this mixes training and test and must not be labeled out-of-sample.
Intratrade mark-to-market maximum drawdown has NOT been measured.

Reproduce with pandas and pyarrow installed in an isolated research environment:
`python research/polymarket_xrp/sample_backtest.py xrp.parquet binance_sample.json`
The aligned CSV and per-trade JSON are included for audit. Original Parquet can be
downloaded from the source and checked against its hash; no need for credentials.
Seven existing correctness tests passed, plus independent compounding and
holdout timestamp checks. Third-party data accuracy has not been independently
reconciled to exchange records. This single few-hour period is far too short for
robust conclusions. Need more days/regimes and intratrade risk measurement.

No production files, Render services, LIVE orders, workflows or paid services changed.
