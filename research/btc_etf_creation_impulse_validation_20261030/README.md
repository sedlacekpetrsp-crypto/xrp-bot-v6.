# BTC_ETF_CREATION_IMPULSE_XRP_V1 — completed validation

Decision: **NEPROŠEL**. The protocol and code were saved remotely in commit `9cdfe5e2edfbe68b99f3e2611f67428b09979bc1` before performance evaluation. No threshold, timing, execution rule or gate changed afterward.

## Data and causality

The retained Farside Investors all-data HTML contains 720 parsed date rows; the frozen cutoff retains 698 finite total-flow observations from 11 January 2024 through 30 September 2026. It produced 407 positive-flow signals. Farside is a third-party compilation rather than an issuer filing or audited primary source. No missing marker was converted to zero and no non-reported date was filled. The source response is identified by URL, 841,631 bytes and local SHA256 `7c7a56af606a1a0e331abd6426a1ff02a16a29ef8f98559fac23ccc81935bba8`.

Two direct Binance Data API responses contain 1,004 consecutive XRPUSDT daily candles from 1 January 2024 through 30 September 2026. Exact URLs, byte sizes and local SHA256 values are in `results.json`. Signals use only the reported ETF total on D and enter at D+2 UTC open. ATR uses preceding closed price candles. There are no price gaps or synthetic prices.

## Results

| Locked period | Base trades | Base P/L | Base PF | Stress P/L | Stress PF |
|---|---:|---:|---:|---:|---:|
| 2024-H2 | 29 | $401.43 | 1.880 | $368.42 | 1.782 |
| 2025-H1 | 26 | -$222.02 | 0.531 | -$245.80 | 0.494 |
| 2025-H2 | 26 | $206.43 | 1.718 | $178.96 | 1.598 |
| 2026-H1 | 22 | -$160.54 | 0.598 | -$187.72 | 0.550 |
| 2026-Q3 | 15 | $155.98 | 1.819 | $133.35 | 1.644 |
| **Annual-reset OOS sum** | **118** | **$381.28** | **1.211** | **$247.20** | **1.131** |

The annual-reset sum is not a compounded return. The separate continuous path has 119 trades, +$396.32, PF 1.214 and 4.61% maximum drawdown at base costs; doubled costs retain +$258.25, PF 1.135 and 4.99% drawdown. The January–June 2024 control loses $182.29 base and $210.62 stressed.

Sample, aggregate net/expectancy/PF, cost stress, final-period and drawdown gates pass. Stability fails because only 3/5 locked OOS periods are positive at either cost level. Profit concentration also fails: the largest positive month supplies 26.83% versus the frozen 25% maximum. No independent forward PAPER evidence exists. These failures cannot be overridden by aggregate profitability.

All 261 repository tests pass. The implementation-independent audit passes 4,689 checks over 520 trade instances across control, fold, continuous, base and stress ledgers. This verifies retained hashes, independent parsing and signals, D+2 causality, price continuity, ATR, fills, gap-stop, costs, sizing, non-overlap and report arithmetic; it does not establish future profitability.

## Reproduction and limitations

```sh
python -m unittest discover -s tests -v
python -m research.run_btc_etf_creation_impulse /tmp/btc-etf-cache research/btc_etf_creation_impulse_validation_20261030
python -m research.audit_btc_etf_creation_impulse /tmp/btc-etf-cache research/btc_etf_creation_impulse_validation_20261030
```

The public source begins only in January 2024, historical publication times are unavailable, and its figures may be revised. The D+2 rule is deliberately conservative but does not reconstruct historical release timestamps. Daily OHLC cannot recover tick paths; the frozen stop-first and gap rules are conservative approximations. Local hashes identify retrieved bytes but are not publisher signatures.

Do not select only profitable half-years, relax concentration, shorten the lag or add a positive-flow magnitude threshold after seeing these results. Do not promote to forward PAPER. The next concrete step is a source-coverage feasibility check for direct XRP Ledger DEX executed-offer/liquidity observations, a market-liquidity mechanism distinct from ETF flow, price, derivatives and the previously tested aggregate on-chain counts. Register it only if exact historical ledgers can be retained without paid data, fabricated spreads or missing-ledger interpolation. Production, Render, LIVE, main and `v8-fly-layer-test` remain untouched.
