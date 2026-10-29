# XRP_FINANCIAL_CONDITIONS_EASING_V1 — completed historical validation

Decision: **NEPROŠEL**. The frozen external financial-conditions hypothesis is rejected and is not promoted to forward PAPER.

The protocol and source decision were committed before performance evaluation. The signal required the Chicago Fed NFCI to be both accommodative (<= -0.25) and at least 0.10 index point lower than eight valid weekly observations earlier. Every NFCI observation was conservatively delayed until the second subsequent valid weekly observation, with entry at the next XRP daily open. No parameter was selected or changed after seeing returns.

## Data and controls

- Direct FRED NFCI CSV: 352 valid weekly observations from 2020-01-03 through 2026-09-25, no duplicate.
- Direct Binance Vision: 81 monthly XRPUSDT daily archives, January 2020 through September 2026; 2,465 unique consecutive days, no gap or duplicate.
- Exact source URLs, byte counts, row counts, missing timestamps and locally computed SHA256 fingerprints are in `results.json`. Hashes identify retrieved bytes and are not publisher signatures.
- A proposed high-yield-spread source was rejected before registration because its free direct export started only on 2023-10-30; no missing history was fabricated.
- Execution: next daily open, long-only spot, one position, 0.5% equity stop risk, 20% notional cap, 2 ATR stop, 3R target, maximum ten days. Base fee/slippage were 9.5/2 bps per side; stress doubled both. Gap stops used the adverse open and same-candle ambiguity favored the stop.
- All 180 repository tests passed. The independent audit passed 404 checks of publication and entry timing, both NFCI thresholds, non-overlap, risk/notional limits, costs, P/L and aggregate gates. Tests prove mechanics, not an edge.

## Locked results

| Annual OOS fold | Base trades | Base net P/L | Base PF | Stress trades | Stress net P/L | Stress PF |
|---|---:|---:|---:|---:|---:|---:|
| 2022 | 0 | $0.00 | n/a | 0 | $0.00 | n/a |
| 2023 | 4 | -$94.64 | 0.066 | 5 | -$67.31 | 0.283 |
| 2024 | 0 | $0.00 | n/a | 0 | $0.00 | n/a |
| 2025 | 1 | +$28.94 | no loss | 1 | +$27.75 | no loss |
| 2026 Jan–Sep | 0 | $0.00 | n/a | 0 | $0.00 | n/a |
| **Annual folds combined** | **5** | **-$65.70** | **0.351** | **6** | **-$39.56** | **0.578** |

Annual-fold expectancy was -$13.14 base and -$6.59 stressed. Different cost fills can change later position availability, hence the stress path has one additional trade. The separate continuous OOS run produced 5 trades, -$65.98, PF 0.349 and 1.26% drawdown; stress produced 6 trades, -$39.75, PF 0.576 and 0.99% drawdown. Continuous and annual runs reuse observations and are not additive.

Only the drawdown gate passed. Sample, net P/L, expectancy, PF, annual stability, final-2026 and concentration gates failed. Zero-trade folds are not profitable years; the positive 2020–2021 control and isolated 2025 trade cannot be selected after observation.

Reproduce from repository root:

```sh
python -m unittest discover -s tests -v
python -m research.run_financial_conditions_easing /tmp/financial-data research/financial_conditions_easing_validation_20261029
python -m research.audit_financial_conditions_easing research/financial_conditions_easing_validation_20261029
```

Do not relax or invert the observed NFCI rules. The next experiment must leave this external easing family and preregister a genuinely different information mechanism. Production, Render, infrastructure, paused strategies and LIVE remain untouched.
