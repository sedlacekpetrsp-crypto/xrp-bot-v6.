# XRP_CORE_DEVELOPMENT_ACTIVITY_V1 — completed exploratory validation

Decision: **NEPROŠEL**.

The fixed protocol, the same-second event-ingestion clarification and the complete source-feasibility record were each committed before performance evaluation. This genuinely different fundamental hypothesis used public integration activity in the canonical `XRPLF/rippled` repository rather than XRP price/flow, sentiment, relative strength, on-chain usage, derivatives, DeFi yield or macro-market inputs.

## Evidence and controls

- 2,262 unique merged pull requests from 32 exhaustively paginated official GitHub Search Issues API payloads, 2020-01-02 through 2026-09-30. Each exact query URL, reported total, page rows, byte count and local SHA256 is in `results.json`.
- 36 events shared a public merge second with another distinct PR. They were retained only under the separately committed pre-performance ingestion clarification; conflicting timestamps for one PR remained fatal.
- 81 direct Binance Vision XRPUSDT daily archives, January 2020 through September 2026: 2,465 unique consecutive candles, no gaps or duplicates. Exact URLs and locally computed SHA256 fingerprints are retained.
- Signals used trailing completed UTC days and entered only at the following daily open. No merge event or price was filled, interpolated or fabricated.
- Base costs were 9.5 bps fee and 2 bps adverse slippage per side; stress doubled both. Sizing risked 0.5% of equity to the initial stop, capped at 20% notional with zero leverage and no overlap. Stop won intrabar ambiguity and gap-stop used the worse open.
- All 206 repository tests passed. An independent audit imported no strategy module and passed all 7,557 API completeness, hash, merge-count, causality, fill, cost, sizing, non-overlap and equity checks.

## Frozen annual OOS results

Annual folds independently reset USD 10,000; their P/L is summed rather than compounded.

| Fold | Trades | Net P/L | PF | Double-cost P/L | Stress PF |
|---|---:|---:|---:|---:|---:|
| 2022 | 0 | $0.00 | — | $0.00 | — |
| 2023 | 20 | $297.70 | 1.806 | $273.00 | 1.720 |
| 2024 | 12 | $17.12 | 1.072 | $5.26 | 1.022 |
| 2025 | 40 | -$285.91 | 0.694 | -$321.96 | 0.661 |
| 2026 through September | 33 | -$143.73 | 0.824 | -$185.57 | 0.779 |
| **Annual OOS aggregate** | **105** | **-$114.81** | **0.951** | **-$229.27** | **0.905** |

The separate continuous 2022–September 2026 path lost $123.61, PF 0.948 and had 7.86% conservative drawdown. Stress lost $237.11, PF 0.903 and had 8.66% drawdown. The frozen 75-trade sample and drawdown gates passed, but net P/L, expectancy, PF, stability, final-year and concentration gates failed. Zero exposure in 2022 is not a profitable year. No independent forward-PAPER evidence exists.

GitHub's historical search index can change if repository metadata is altered; local hashes identify the exact responses but are not publisher signatures. Merge count weights every PR equally and does not prove code quality, release timing or adoption. Daily OHLC execution remains a conservative approximation, not tick-exact evidence.

Reject without reversing the signal, changing merge thresholds, selecting 2023–2024 or weighting PRs after observing returns. Do not promote to forward PAPER. The next concrete step is another genuinely distinct preregistered data mechanism, not further mining of these merge-count windows. No production, main, `v8-fly-layer-test`, Render, paused strategy or LIVE setting was changed.

Reproduce from repository root:

```sh
python -m unittest discover -s tests -v
python -m research.run_core_development_activity /tmp/core-dev-cache research/core_development_activity_validation_20261029
python -m research.audit_core_development_activity /tmp/core-dev-cache research/core_development_activity_validation_20261029
```
