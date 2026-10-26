# XRP_ILLIQUIDITY_SHOCK_REVERSAL_V1 — completed validation

Decision: **NEPROŠEL**. Rules and gates were frozen in GitHub commit `02175691272e35c5614ae8f1204b1ab7226b2403`. The zero-volume/no-imputation ingestion amendment was frozen in `f2173f512dc92ebc6aead05123562a15431579f1`, after the first run stopped and before any performance was computed.

The screen used 57 real Binance Vision monthly XRPUSDT spot 1h archives, January 2022–September 2026: 41,615 bars, no duplicates. Source URLs, byte counts and locally computed SHA256 fingerprints are in `results.json`. One real zero-volume row was retained; the missing 2023-03-24 13:00 UTC hour was not filled, and affected causal windows were suppressed.

Across 15 quarterly OOS folds, 213 non-overlapping base-cost trades lost **$1,065.48**, PF **0.7475**, expectancy **-$5.00/trade**. Doubled fee/slippage produced the same 213 trades and lost **$2,020.26**, PF **0.5800**, expectancy **-$9.48/trade**. Only 6/15 quarters were positive. Continuous OOS drawdown was 12.76% base and 19.03% stressed. The 2022 control also lost $406.22 base and $796.55 stressed. Only the sample-size and final-quarter base gates passed; profitability, stress, stability, drawdown and concentration gates failed.

All 77 repository tests passed. The separate audit, which imports no strategy code, passed 8,448 chronology, non-overlap, cost, sizing and reconciliation checks. Tests and audit establish mechanics, not profitability. Full metrics and provenance are in `results.json`; complete ledgers are in `trades.json.gz`; audit output is in `audit.json`.

No parameters were changed after viewing results. Do not tune the return or impact percentile on these observed folds and do not promote to forward PAPER or production. Next concrete step: preregister a genuinely distinct mechanism using information other than single-market hourly price impact; preserve a new forward interval for any historically viable candidate.
