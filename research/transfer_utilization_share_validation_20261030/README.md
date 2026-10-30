# XRP_TRANSFER_UTILIZATION_SHARE_V1 — completed validation

Decision: **NEPROŠEL**. The compositional hypothesis, 180-day lookback, nearest-rank 80th percentile, two-day lag, execution and gates were stored in GitHub commit `925282d4d3016688bf6ab56edb95526782cf00e8` before performance. Initial ingestion stopped before any signal or trade because the full CoinMetrics response contains one 2013 genesis row with a zero denominator. Commit `98070281cd4e7b928cf12e56e38c1c8e6c64aa41` froze the pre-result rule to retain data from 2019 onward, still more than the entire 180-day warm-up; nothing was imputed and strategy parameters did not change.

This tests the fraction of transactions containing value transfers, `TxTfrCnt/TxCnt`, not the rejected absolute active-address/transaction breadth rule. The direct CoinMetrics payload has 5,050 raw rows and SHA256 `845d37f3a7599e7762e015a35bc0149753ce5d7813b43de5708076446ac2c106`. After the preregistered-window amendment, 2,859 daily metric rows from 2019-01-01 are consecutive with no duplicate or gap. Eighty-one direct Binance Vision archives provide 2,465 consecutive XRP daily candles from 2020-01-01 through 2026-09-30. Exact URLs, bytes and every SHA256 are in `results.json`. No metric or price was filled.

All 228 repository tests passed. The independent audit passed 4,290 checks of hashes, transfer share, past-only nearest-rank threshold, two-day lag, chronology, actual opens, adverse fills, fees, slippage, risk, cap, non-overlap, equity and reports without importing strategy code. Passing tests establish mechanics, not profitability.

| Annual OOS fold | Trades | Base net P&L | Base PF | Double-cost net P&L | Stress PF |
|---|---:|---:|---:|---:|---:|
| 2022 | 16 | -$132.73 | 0.574 | -$148.56 | 0.538 |
| 2023 | 22 | +$231.75 | 1.708 | +$205.78 | 1.609 |
| 2024 | 10 | -$124.56 | 0.301 | -$134.83 | 0.266 |
| 2025 | 13 | +$12.12 | 1.039 | +$0.60 | 1.002 |
| 2026 through September | 7 | -$27.04 | 0.717 | -$36.33 | 0.642 |
| Aggregate reset folds | 68 | -$40.46 | 0.967 | -$113.34 | 0.910 |

Base expectancy is -$0.59 per trade and stressed expectancy -$1.67. The separate continuous OOS path has 68 repeated trades, -$44.68/PF 0.963 with 3.10% conservative drawdown; stress is -$116.77/PF 0.907 with 3.31% drawdown. The 2020–2021 control is profitable, but it was not used for selection and cannot override later OOS losses. Annual and continuous observations are repeated evidence and are not added.

The candidate fails the frozen 120-trade sample, net, expectancy, PF, annual stability, final-year and concentration gates at both cost levels. Only 2023 and marginally 2025 are positive. No forward PAPER evidence exists. `TxTfrCnt` counts transfers rather than economically unique users, and the ratio is not direct adoption evidence.

Reproduce from repository root:

```sh
python -m unittest discover -s tests -v
python -m research.run_transfer_utilization_share /tmp/transfer-share-cache research/transfer_utilization_share_validation_20261030
python -m research.audit_transfer_utilization_share /tmp/transfer-share-cache research/transfer_utilization_share_validation_20261030
```

Full ledgers are in `trades.json.gz`; metrics, sources and gates in `results.json`; audit in `audit.json`. Do not tune or invert the share threshold or combine this post hoc with the earlier breadth near-signal. Next research must leave transaction-count composition and use a genuinely different preregistered mechanism. Production, main, `v8-fly-layer-test`, Render, paused strategies, infrastructure and LIVE were untouched.
