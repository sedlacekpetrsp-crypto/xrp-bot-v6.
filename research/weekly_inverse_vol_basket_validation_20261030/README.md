# CRYPTO_WEEKLY_INVERSE_VOL_BASKET_V1 — completed validation

Decision: **NEPROŠEL**. Do not tune the universe, volatility window, cap, stop or rebalance schedule on these observations, and do not start forward PAPER.

The fixed protocol, code and mechanics tests were saved remotely before performance evaluation in commit `961aa4365a8f702af2cb64fb78dc17ffa0cce859`. The mechanism differs from rejected relative-strength and volatility-breakout studies: all three assets are held concurrently, return direction is never used, and only each asset's past realized-volatility magnitude determines portfolio weights.

## Data and verification

The run used nine direct Binance public Data API responses: XRPUSDT, BTCUSDT and ETHUSDT daily spot OHLC from 2020-01-01 through 2026-09-30. Each market contains 2,465 rows, with exact cross-market timestamps, no duplicates and no missing UTC days. `results.json` retains every exact request URL, response size and local SHA256. These hashes identify downloaded bytes; they are not publisher signatures. No price was imputed.

All 240 repository research tests passed, including seven new tests for past-only features, inverse-volatility caps, aligned calendars, simultaneous sleeves, per-asset non-overlap, gap-stop fills, P/L identities and double-cost deterioration. The independent audit does not import the strategy implementation and passed all 43,923 checks across 3,288 base/stress/control/continuous ledger records. Tests and audits verify mechanics, not future profitability.

## Frozen-gate results

| Annual OOS folds, reset capital | Trades | Net P/L | PF | Expectancy | Fees | Slippage cost |
|---|---:|---:|---:|---:|---:|---:|
| Base costs | 744 | +$4,147.21 | 1.060 | +$5.57 | $4,422.35 | $931.02 |
| Double costs | 744 | -$1,718.44 | 0.975 | -$2.31 | $8,349.47 | $1,757.78 |

The annual-fold sum resets $10,000 each year and is not a compounded portfolio return. The separate continuous 2022–September 2026 diagnostic lost $3,023.92 at base costs (PF 0.951, conservative drawdown 69.77%) and $6,032.74 under double costs (PF 0.875, drawdown 74.69%). It reuses the same observations and is not additional evidence.

| Year | Base net P/L | Double-cost net P/L |
|---|---:|---:|
| 2022 | -$6,023.97 | -$6,466.77 |
| 2023 | +$9,502.78 | +$7,317.39 |
| 2024 | +$6,943.53 | +$5,022.20 |
| 2025 | -$4,376.03 | -$5,003.44 |
| 2026 through September | -$1,899.11 | -$2,587.83 |

At base costs XRP contributed +$4,937.88, BTC +$1,058.45 and ETH -$1,849.13. Under stress XRP contributed +$2,841.32, BTC -$1,104.27 and ETH -$3,455.50. Only 2/5 OOS years were profitable, the final year lost, and 2023 supplied 57.78% of positive annual profit. The candidate fails frozen PF, stress net/expectancy/PF, all-asset, year stability, final-year, drawdown and concentration gates. The adequate 744-trade count and positive base annual-reset sum cannot override those failures.

The strategy is long-only and therefore includes broad crypto beta; no claim of alpha follows from profitable subsets. Full weekly liquidation/re-entry is conservative, but daily OHLC still cannot reconstruct ticks, latency, taxes or exact intraday paths. Gap-stops use the worse open and intraday stops use the frozen stop with adverse slippage. No leverage or borrowing was modeled, and each target weight remained <=50%.

Reproduce from repository root:

```sh
python -m unittest discover -s tests -v
python -m research.run_weekly_inverse_vol_basket /tmp/weekly-inverse-vol-cache research/weekly_inverse_vol_basket_validation_20261030
python -m research.audit_weekly_inverse_vol_basket /tmp/weekly-inverse-vol-cache research/weekly_inverse_vol_basket_validation_20261030
```

Next concrete step: do not create a portfolio-window variant. First perform a source-coverage feasibility check for an official historical BTC options 25-delta risk-reversal surface, which would test asymmetric tail-risk pricing rather than realized-volatility allocation or the already rejected variance-risk-premium level. Preregister only if the source provides timestamped, reproducible multi-year observations without reconstructing missing quotes.

No production bot, main, `v8-fly-layer-test`, Render, infrastructure, paused strategy or LIVE trading was touched.
