# XRP_FLOAT_EXPANSION_SLOWDOWN_V1 — completed validation

Decision: **NEPROŠEL**. The tokenomics hypothesis, 30-day change, past-only 365-day nearest-rank 20th percentile, two-day lag, execution and gates were stored in GitHub commit `e43e883463d15d5acc383b66cf1c2f4e0bb92808` before performance. No parameter or methodology changed after results.

The direct CoinMetrics ratio `CapMrktEstUSD/CapMrktCurUSD` cancels the shared XRP price and proxies estimated circulating supply as a fraction of current/full supply. This tests relative float-expansion slowdown, not price valuation, holder growth, transaction activity, fee, flow or market-cap level. The retained raw response has SHA256 `7af6273b65d923462e1a849fe960992fe08f8b57c357b854a23362050e38a432`. It contains 2,687 consecutive valid estimated/current-cap days from 2019-06-22, with zero gaps or duplicates; 1,772 earlier rows lacking the estimated metric were explicitly excluded. Eighty-one Binance Vision archives contain 2,465 consecutive XRP daily candles from 2020-01-01 through 2026-09-30. Nothing was filled.

All 233 repository tests passed. The independent audit passed 2,794 checks of hashes, price-cancelling ratio, 30-day percentage-point change, past-only nearest-rank threshold, lag, chronology, fills, fees, slippage, risk, cap, non-overlap, equity and reports without importing strategy code. Tests establish mechanics, not profitability.

| Annual OOS fold | Trades | Base net P&L | Base PF | Double-cost net P&L | Stress PF |
|---|---:|---:|---:|---:|---:|
| 2022 | 12 | -$74.54 | 0.642 | -$85.06 | 0.600 |
| 2023 | 1 | -$51.23 | 0.000 | -$52.45 | 0.000 |
| 2024 | 17 | +$582.44 | 2.876 | +$562.30 | 2.766 |
| 2025 | 12 | -$328.95 | 0.207 | -$339.85 | 0.197 |
| 2026 through September | 14 | -$49.23 | 0.852 | -$65.07 | 0.810 |
| Aggregate reset folds | 56 | +$78.49 | 1.060 | +$19.86 | 1.015 |

Aggregate expectancy is +$1.40 base and +$0.35 stressed, but PF is far below the frozen 1.20/1.05 gates. The separate continuous OOS path has 56 repeated trades, +$56.25/PF 1.042 and 5.24% conservative drawdown; double-cost stress is -$2.00/PF 0.999 and 5.51% drawdown. The 2021 control is only marginally positive. Annual and continuous trades are repeated evidence and are not added.

The candidate fails the 120-trade sample, PF, four-of-five-year stability, final-2026 and concentration gates. Four of five OOS years lose at both costs; 2024 alone supplies more than all aggregate profit and masks later 2025–2026 losses. Only aggregate net/expectancy and drawdown pass. No independent forward PAPER evidence exists. A low estimated float-growth pace is not proof of actual escrow selling, and CoinMetrics' estimated-supply methodology can revise.

Reproduce from repository root:

```sh
python -m unittest discover -s tests -v
python -m research.run_float_expansion_slowdown /tmp/float-cache research/float_expansion_slowdown_validation_20261030
python -m research.audit_float_expansion_slowdown /tmp/float-cache research/float_expansion_slowdown_validation_20261030
```

Full ledgers are in `trades.json.gz`; metrics, sources and gates in `results.json`; audit in `audit.json`. Do not select 2024, lower the sample/PF gates or tune the float windows. Next work must leave estimated-supply/float variants and use a distinct preregistered mechanism or genuinely independent future evidence. Production, main, `v8-fly-layer-test`, Render, paused strategies, infrastructure and LIVE were untouched.
