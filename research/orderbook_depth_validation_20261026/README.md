# XRP_ORDERBOOK_DEPTH_IMBALANCE_V1 — completed validation

Decision: **NEPROŠEL**. The fixed protocol was stored in commit `d5fa1c2b17a07aa6d4119ba3142ba4a9a15ed8bc`; the missing-archive rule was stored in `8317b33bb5cf83948978f057eb291117cc89fdc1`, both before performance calculation.

The run inspected 1,004 requested daily Binance Vision futures `bookDepth` archives and 33 monthly XRPUSDT spot 1h archives for January 2024–September 2026. There are 1,036 downloaded source SHA256 fingerprints and one explicit publisher 404 (2026-01-14). No prices or depth were fabricated.

The exact frozen 59:30 selection produced only 4,021 depth/spot-aligned hours versus 24,096 spot hours and 2,557 discontinuities. No consecutive 720-hour history existed, therefore the causal signal correctly produced **0 control and 0 OOS trades**. The minimum 150-trade gate and all profitability/stability gates failed. Zero P/L and zero drawdown are absence of evidence, not evidence of safety or profitability.

All 83 repository unit tests passed. The independent audit confirms an empty ledger, 1,037 manifest entries, 1,036 hashes and one missing entry; it had no trade arithmetic to check. Complete source manifest, quality report and gates are in `results.json`; the empty scenario ledgers remain in `trades.json.gz` and audit metadata in `audit.json`.

Do not relax timestamp selection or shorten the causal lookback after observing this outcome under the V1 name. A future, separately preregistered order-book study may define a causal last-observation-before-hour resampling rule only after first documenting snapshot cadence on a non-evaluation calibration slice. No forward PAPER promotion.

