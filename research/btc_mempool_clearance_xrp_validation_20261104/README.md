# BTC_MEMPOOL_CLEARANCE_XRP_V1 — final validation

Final decision on 2026-11-04: **NEPROSEL**. Offline research only; no forward PAPER promotion or deployment.

## Frozen mechanism and sources

The remotely preregistered hypothesis tested whether unusually low Bitcoin settlement congestion preceded positive weekly XRP expectancy. It used no XRP/BTC price direction, relative strength, volume, order book, exchange flow, derivatives, macro, hashrate or XRP activity count. On Friday only, the daily median BTC mempool size had to be at or below the empirical lower tercile of the strictly preceding 365 valid daily medians. Entry was the Monday XRP open, a full 48 hours after Friday closed.

The fixed Blockchain.com query supplied 271,560 used intraday mempool observations from 2019-01-01 through 2026-09-30. Aggregation produced 2,830 consecutive UTC days, with 67–96 unique samples per day versus the frozen minimum 64; no day or value was filled. Three direct Binance Data API responses supplied 2,465 consecutive XRPUSDT daily candles from 2020-01-01 through 2026-09-30. `results.json` preserves exact URLs, byte counts and local SHA256 fingerprints.

The first performance output was explicitly invalidated after the independent audit found a fold-boundary accounting defect: a final partial-week position affected drawdown but was silently absent from trades and realized PnL. The defect, correction and regression test were documented and committed before rerun. The corrected simulator realizes any open boundary position at the last actual close with normal exit costs and reason `FOLD_END`. No signal, source, threshold, date, sizing, cost or acceptance gate changed. Only the corrected rerun below is evaluated.

## Corrected locked OOS result

The five annual-reset OOS folds contain 95 non-overlapping trades and lose **$129.58**, with **PF 0.9130**, **-$1.36 expectancy**, $78.84 fees and $16.60 modeled slippage. The same trades under doubled fees and slippage lose **$222.42**, with **PF 0.8560**, **-$2.34 expectancy**, $157.42 fees and $33.14 modeled slippage.

Annual base net PnL for 2022–2026 is -$12.32, +$59.34, +$175.98, -$227.90 and -$124.67. Stress PnL is -$19.16, +$58.09, +$151.63, -$276.02 and -$136.95. Only 2023 and 2024 are positive at both cost levels; final 2026 loses. The separate continuous OOS path loses $35.97 base and $129.15 stressed, with 4.55% and 5.07% maximum drawdown. The largest positive month supplies 40.61% of positive monthly profit, above the frozen 25% limit.

The sample and drawdown gates pass. Net, expectancy, PF, yearly stability, final-year and concentration gates fail at both costs. The 2020–2021 control also loses. There is no independent forward PAPER evidence. Reject without changing the tercile, choosing 2023–2024, reversing the signal or adding a price filter.

## Verification and artifacts

- `results.json`: corrected metrics, gates, data-quality checks and source manifests.
- `daily_metric.json.gz`: all 2,830 derived daily mempool observations and sample counts.
- `trades.json.gz`: every corrected fold and cost-scenario trade ledger.
- `audit.json`: independent reconstruction passed 7,185 checks, including 434 trade checks, with zero failures.
- `unit_tests.txt`: all 276 repository tests passed.

Reproduce from repository root with:

```bash
python -m research.run_btc_mempool_clearance_xrp CACHE_DIR research/btc_mempool_clearance_xrp_validation_20261104
python -m research.audit_btc_mempool_clearance_xrp CACHE_DIR research/btc_mempool_clearance_xrp_validation_20261104
python -m unittest discover -s tests -v
```

Blockchain.com chart data can be revised and local SHA256 values are not publisher signatures. Low mempool backlog can also mean weak demand rather than healthy capacity. Daily OHLC cannot reproduce tick paths; the fixed simulator uses conservative ambiguity and gap rules.

Next step: close this BTC congestion family. Check whether Ripple/XRPL documentation supplies a complete canonical list of escrow-owning accounts and whether their immutable `account_tx` histories can reproduce EscrowCreate/EscrowFinish amounts without global-state enumeration or imputation. Preregister a supply-lock hypothesis only if that universe is complete. Production, Render, LIVE, main and `v8-fly-layer-test` remain untouched.
