# XRP_REAL_YIELD_EASING_V1 — completed historical validation

Decision: **NEPROŠEL**. The frozen external real-rate hypothesis does not qualify for forward PAPER promotion.

The protocol was committed before evaluation. It used the FRED DFII10 ten-year real Treasury yield, assigned each observation to the date of the second subsequent valid observation, and bought XRP at the following daily open only after a 20-valid-observation decline of at least 0.25 percentage point. No threshold or exit was tuned after results.

## Data and mechanics

- Direct FRED CSV: 1,761 raw rows, 1,689 valid observations; missing values were excluded without fill or interpolation.
- Direct Binance Vision: 81 monthly XRPUSDT daily archives, January 2020 through September 2026; 2,465 unique consecutive days, no gap or duplicate.
- Exact direct URLs, byte counts, row counts, missing timestamps and locally computed SHA256 values are in `results.json`. The hashes identify retrieved bytes and are not publisher signatures.
- Entry was the next daily open; one spot position maximum; 0.5% equity risk to a 2 ATR stop; 20% notional cap; 3R target; 10-day maximum hold.
- Base costs were 9.5 bps fee and 2 bps adverse slippage per side; stress doubled both. Gap stops used the adverse open and same-candle stop/target ambiguity favored the stop.
- All 174 repository tests passed. The independent implementation-free ledger audit passed 1,066 checks covering release and entry lag, signal threshold, non-overlap, stop risk, notional, fees, slippage, P/L, aggregate counts and decision gates. Passing mechanics are not profitability evidence.

## Locked chronological results

| Annual OOS fold | Base trades | Base net P/L | Base PF | Stress net P/L | Stress PF |
|---|---:|---:|---:|---:|---:|
| 2022 | 6 | -$110.95 | 0.273 | -$116.34 | 0.252 |
| 2023 | 7 | +$101.71 | 6.280 | +$94.36 | 5.377 |
| 2024 | 8 | -$191.79 | 0.266 | -$199.94 | 0.252 |
| 2025 | 3 | -$79.59 | 0.219 | -$82.03 | 0.210 |
| 2026 Jan–Sep | 0 | $0.00 | n/a | $0.00 | n/a |
| **Annual folds combined** | **24** | **-$280.64** | **0.476** | **-$303.94** | **0.446** |

Combined annual-fold expectancy was -$11.69 base and -$12.66 stressed. The separately simulated continuous January 2022–September 2026 path produced 23 trades, -$272.91, PF 0.481 and 3.04% drawdown; stress produced -$294.34, PF 0.452 and 3.24% drawdown. Continuous and annual runs reuse observations and must not be added together.

Only the drawdown gate passed. Sample size, base/stressed net P/L, expectancy, PF, annual stability, final-2026 activity and concentration gates failed. Zero trades in 2026 are not a profitable fold. The positive 2020–2021 control and 2023 OOS subset do not justify selecting periods or changing the rule after observation.

Reproduce from repository root:

```sh
python -m unittest discover -s tests -v
python -m research.run_real_yield_easing /tmp/real-yield-data research/real_yield_easing_validation_20261029
python -m research.audit_real_yield_easing research/real_yield_easing_validation_20261029
```

Do not invert or tune this observed rates signal. A next experiment must freeze a genuinely different mechanism before evaluation. No production, Render, infrastructure, paused strategy or LIVE setting was changed.
