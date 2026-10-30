# BTC_HASHRATE_SHOCK_RECOVERY_XRP_V1 — completed validation

Decision: **NEPROŠEL**. The completed strategy loses at both cost levels and in four of five OOS years. Do not tune the z-score, lookback or recovery rule and do not start forward PAPER.

The protocol, code, downloader, audit and mechanics tests were saved remotely in commit `e806f3661f19f148c449821b075ac29c6d4ad0d8` before performance evaluation. This is a network-security mechanism based on BTC estimated hashrate, distinct from price/volume/derivatives, XRP transaction activity and the closed options family.

## Data and verification

The direct CoinMetrics Community response contains 6,503 positive daily BTC `HashRate` observations from 2009-01-09 through 2026-10-29. The tested 2020–September 2026 window is consecutive with no missing day. Three direct Binance Data API responses contain 2,465 consecutive XRPUSDT daily spot candles from 2020-01-01 through 2026-09-30. No value or candle was imputed. Exact URLs, response sizes and local SHA256 fingerprints are in `results.json`; local hashes are not publisher signatures.

All 254 repository research tests passed, including seven new tests for the excluded 30-day population-statistics window, recovery condition, two-day lag, gap rejection, causal invariance, gap-stop and sizing. The independent audit re-read the raw responses and passed all 5,214 checks across 578 base/stress/control/continuous ledger records. Tests and audits validate mechanics, not profitability.

## Frozen-gate results

| Annual OOS folds, reset capital | Trades | Net P/L | PF | Expectancy | Fees | Slippage cost |
|---|---:|---:|---:|---:|---:|---:|
| Base costs | 132 | -$911.20 | 0.623 | -$6.90 | $119.70 | $25.20 |
| Double costs | 132 | -$1,051.24 | 0.579 | -$7.96 | $239.08 | $50.33 |

| Year | Base net P/L | Double-cost net P/L |
|---|---:|---:|
| 2022 | -$500.62 | -$526.29 |
| 2023 | -$264.90 | -$285.71 |
| 2024 | +$354.36 | +$319.13 |
| 2025 | -$220.76 | -$245.44 |
| 2026 through September | -$279.28 | -$312.94 |

The separate continuous OOS diagnostic has 133 trades and loses $944.08, PF 0.599, drawdown 9.56%; double costs lose $1,073.30, PF 0.557, drawdown 10.85%. It reuses the same observations and is not extra evidence. The signal has adequate coverage (46/31/45/43/46 entry-year signals in 2022–2026 before overlap handling), but only 2024 is profitable. Base/stress net, expectancy, PF, annual stability, final-year, stress drawdown and monthly concentration gates fail.

Daily `HashRate` is an estimate based on observed block production and may be revised. A one-standard-deviation shortfall can reflect Poisson sampling noise rather than true miner capitulation. This limitation was frozen before results and cannot rescue the losing evidence.

Reproduce from repository root:

```sh
python -m unittest discover -s tests -v
python -m research.run_btc_hashrate_shock_recovery /tmp/btc-hashrate-recovery-cache research/btc_hashrate_shock_recovery_validation_20261030
python -m research.audit_btc_hashrate_shock_recovery /tmp/btc-hashrate-recovery-cache research/btc_hashrate_shock_recovery_validation_20261030
```

Next concrete step: leave the hashrate family closed. Perform a source-coverage feasibility check for daily US spot BTC ETF creations/redemptions or issuer-reported fund flows, which would test institutional primary-market demand rather than price, network, derivative or on-chain activity. Preregister only if actual, date-stamped multi-fund observations can be retained with hashes without using a paid service or fabricating missing days.

No production bot, main, `v8-fly-layer-test`, Render, infrastructure, paused strategy or LIVE trading was changed.
