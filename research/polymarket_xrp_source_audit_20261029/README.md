# POLYMARKET_XRP_SIGNAL_V1 — source audit, historical test not completed

Decision: **TEST NEDOKONČEN**. No profitability conclusion was made.

The strategy protocol and all performance gates were committed before this audit. It specifies a causal Up-probability signal at minute two of each official five-minute XRP market, a next-minute Binance spot entry, fixed sizing and costs, and requires at least two full calendar years of official source history before performance evaluation.

## Verified official data

- Gamma series `xrp-up-or-down-5m`, ID 10685, recurrence 5m, was created 2025-11-21 21:46:35 UTC.
- The first ascending page contains 100 closed five-minute events beginning 2025-12-18 04:30 UTC. At the fixed audit date, this provides at most 314 days from the earliest returned event and the series itself is only 341 days old, both below the frozen 730-day gate.
- Probe market `xrp-updown-5m-1776494100` is an official Chainlink XRP/USD Up/Down event for 2026-04-18 06:35–06:40 UTC with reported volume $8,912.92.
- The public trades endpoint returned 277 actual trade records with condition/token identities and timestamps.
- Both the legacy CLOB price-history endpoint and the current Data API v2 price-history endpoint returned zero price points for that same resolved, traded market. Trade records can reconstruct matched trades, but not historical best bid/ask or unfilled liquidity.
- Six direct endpoint URLs, payload byte counts and SHA256 fingerprints are retained in `source_audit.json`. No webpage odds, Binance price proxy, resolution value or fabricated Polymarket record was substituted.

All 186 repository tests passed, including new tests for series/event identity, exact five-minute duration, Up-token mapping, trade validation and incomplete-history classification. The independent saved-result audit passed 15 checks. These establish source handling, not strategy profitability.

The 95% daily completeness and 1,000 eligible-market gates remain false/unproven because the earlier mandatory two-year gate already fails. A short 2026-only performance test would violate the preregistered multi-year requirement and invite period selection. The correct classification is therefore TEST NEDOKONČEN, not NEPROŠEL.

Reproduce from repository root:

```sh
python -m unittest discover -s tests -v
python -m research.run_polymarket_xrp_source_audit research/polymarket_xrp_source_audit_20261029
python -m research.audit_polymarket_xrp_source research/polymarket_xrp_source_audit_20261029
```

Next concrete step: accumulate immutable forward snapshots/trades or obtain a complete official archive; only after unchanged two-year and completeness gates pass may the frozen chronological Binance performance test run. No production, Render, infrastructure, paused strategy or LIVE setting was changed.
