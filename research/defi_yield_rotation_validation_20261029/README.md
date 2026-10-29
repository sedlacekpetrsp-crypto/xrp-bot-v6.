# DEFI_YIELD_ROTATION_XRP_V1 — completed exploratory validation

Decision: **NEPROŠEL**. Positive aggregate history is not sufficient evidence for promotion.

The fixed protocol was committed before any performance evaluation, followed by a source-feasibility commit. This is a distinct DeFi capital-allocation hypothesis: declining realized USDC supply APY on the largest ordinary Aave v3 Ethereum USDC pool was treated as a lower opportunity cost for holding XRP. No pool, threshold, exit or period was selected from returns.

## Data and controls

- DefiLlama pool `aa70268e-4b52-42bf-a116-608b370f9501`: 1,362 unique observations from 2023-02-06 through 2026-10-29, no null APY. The exact history payload SHA256 is `d6b3af9afa3fc5148e767a52dc542ad8ed9ba9ed2076d40dd9f180b42a9b6ad1`.
- 45 direct Binance Vision XRPUSDT daily archives, January 2023 through September 2026: 1,369 unique consecutive candles and no gaps. Every URL, byte count, row count and locally computed SHA256 is in `results.json`.
- The first XRP daily open strictly after each source timestamp was used. No source value or candle was filled or invented. Duplicate entry dates would collapse to one signal; none of the raw timestamp histories were duplicated.
- Fees were 9.5 bps per side and adverse slippage 2 bps per side; stress doubled both. Risk was 0.5% of current fold equity, capped at 20% notional with no leverage or overlap. Stop-before-target ambiguity and worse-open gap stops were enforced.
- All 199 repository tests passed. The independent audit imported no strategy code and passed all 2,682 raw-hash, chronology, fill, fee, slippage, risk, cap, non-overlap and equity-reconciliation checks.

## Frozen OOS results

Annual folds independently reset USD 10,000 equity; their P/L is summed and is not a compounded return.

| Fold | Trades | Net P/L | PF | Double-cost P/L | Stress PF |
|---|---:|---:|---:|---:|---:|
| 2024 | 23 | $302.23 | 1.858 | $280.56 | 1.774 |
| 2025 | 18 | $96.95 | 1.319 | $82.31 | 1.266 |
| 2026 through September | 6 | -$69.46 | 0.423 | -$76.46 | 0.397 |
| **Annual OOS aggregate** | **47** | **$329.72** | **1.425** | **$286.41** | **1.358** |

The separate continuous 2024–September 2026 path earned $329.86, PF 1.417 and had 2.53% conservative drawdown; stress earned $285.93, PF 1.352 and had 2.61% drawdown. November 2024 supplied 35.6% of summed positive-month profit, within the frozen 50% limit. The source/control 2023 fold was also positive, but it is not OOS evidence and is not added to the sample.

The frozen minimum was 75 annual-fold OOS trades, but only 47 occurred. The 2026 fold lost at both cost levels, so the required all-fold stability also failed. No independent forward-PAPER evidence exists. Therefore the candidate fails even though aggregate P/L, expectancy, PF, cost stress, drawdown and concentration pass.

The discovery endpoint is a current pool catalog and therefore carries pool-survivorship risk. DefiLlama is a third-party aggregator whose history may be revised; local hashes identify exact downloaded bytes but are not publisher signatures. Daily OHLC cannot reveal intrabar path, so execution and drawdown are conservative approximations rather than tick-exact results.

Do not lower the sample gate, select only 2024–2025, change the APY thresholds, or call the historical result forward evidence. The next concrete step is a genuinely different preregistered mechanism; this rule may only be reconsidered after unchanged, independently accrued future observations. No production, Render, main, `v8-fly-layer-test`, paused strategy or LIVE setting was changed.

Reproduce from repository root:

```sh
python -m unittest discover -s tests -v
python -m research.run_defi_yield_rotation /tmp/defi-yield-cache research/defi_yield_rotation_validation_20261029
python -m research.audit_defi_yield_rotation /tmp/defi-yield-cache research/defi_yield_rotation_validation_20261029
```
