# XRP_SPOT_PERP_CARRY_V1 — completed validation

Decision: **NEPROŠEL**. The market-neutral funding-carry hypothesis failed the frozen historical gates and is not eligible for forward PAPER promotion.

The rules and gates were frozen in GitHub commit `995eca12a921d31bd20f2cb9b08939013ccc3524` before the strategy code was evaluated. No parameter was changed after observing returns.

## Evidence

- 171 actual Binance Vision monthly archives: XRPUSDT spot 1h, USD-M perpetual mark-price 1h, and actual funding records, January 2022 through September 2026.
- Every source URL, downloaded byte count, row count, and locally calculated SHA256 fingerprint is in `results.json`. These fingerprints identify downloaded bytes; they are not publisher signatures.
- Exact timestamp intersection produced 41,543 aligned hourly bars. There were no within-stream duplicates. Seventy-two spot-only hours and one mark-only hour were excluded, leaving two 24-hour gaps before OOS, one common missing hour in 2023, and one 24-hour mark-data gap in 2026. No price was fabricated and no position crossed a gap.
- All 99 repository tests passed. The separate ledger audit passed 3,918 chronology, non-overlap, sizing, cost, P/L-reconciliation, manifest, and hash checks.

| Locked period | Base trades | Base net P/L | Base PF | Stress net P/L | Stress PF |
|---|---:|---:|---:|---:|---:|
| 2022 control | 0 | $0.00 | n/a | $0.00 | n/a |
| 2023 OOS | 25 | -$604.14 | 0.000 | -$690.90 | 0.000 |
| 2024 OOS | 111 | -$2,984.11 | 0.000 | -$3,266.71 | 0.000 |
| 2025 OOS | 3 | -$96.94 | 0.000 | -$107.88 | 0.000 |
| 2026 OOS through September | 0 | $0.00 | n/a | $0.00 | n/a |
| Aggregate annual OOS folds | 139 | -$3,685.19 | 0.000 | -$4,065.49 | 0.000 |
| Continuous Jan 2023–Sep 2026 | 139 | -$3,471.87 | 0.000 | -$3,799.54 | 0.000 |

Annual-fold totals differ from the continuous path because each fold resets equity to $10,000; the observations are repeated and must not be combined as independent evidence. Base annual-fold expectancy was -$26.51 per trade; stress expectancy was -$29.25. Continuous drawdown was 34.72% base and 38.00% stress. All 139 continuous trades lost: 138 conservative pair stops and one basis exit. The short legs collected only $24.15 in observed funding on the continuous base path, far below transaction costs and adverse spread movement.

The frozen intrabar stop intentionally uses simultaneous adverse `mark high` and `spot low` extrema when tick ordering is unknown. This can overstate realizable loss because those extrema may occur at different moments, but it was preregistered, is conservative, and cannot be relaxed after seeing this result. The mark price is also a proxy rather than an executable futures bid/ask. These limitations do not rescue the candidate: it fails sample-adjusted profitability, stress, stability, final-year, drawdown, and concentration gates under its declared methodology.

Reproduce from repository root:

```sh
python -m unittest discover -s tests -v
python -m research.run_spot_perp_carry /tmp/crypto-archives research/spot_perp_carry_validation_20261027
python -m research.audit_spot_perp_carry research/spot_perp_carry_validation_20261027
```

No forward PAPER run is opened for a historically rejected strategy. No production, main, `v8-fly-layer-test`, Render, infrastructure, paused strategy, or LIVE trading setting was changed.

Next concrete step: do not retune carry thresholds or stops on these observed years. Before another evaluation, preregister a genuinely different observable mechanism based on actual forced-liquidation event records (if a complete free archive with stable schema and verifiable provenance is available); otherwise record the data-access failure before choosing another family.

