# XRP radar — historical data quality gate
Status: PROPOSED, NOT RUN. PAPER only.

## Minimum evidence before any performance backtest
1. Dataset inventory: exact venue, symbol, source URL/API, coverage start/end, granularity, UTC, retrieval time, SHA256, license and missingness.
2. Trade/reference coverage: first valid trade 00:05:00–00:06:00 UTC; mark no-reference, outages, price anomalies; ensure complete 336h window before negative label.
3. As-of audit: features must have publication and collector timestamps <= decision timestamp; no retrospective wallet tagging or revised ETF data silently projected backwards.
4. Event QA: sample manually reviewed exact -20% hits, near misses, boundary at 336h, post-cutoff trades, gaps, and isolated bad prints. Validate on second price source.
5. Split audit: purge label overlap (14d downside / 30d growth), nested tuning and calibration, no global scaling, no future-defined regimes.
6. Baselines and leakage: price-only logistic baseline, volatility, BTC regime, lag tests and deliberately impossible future-shift leakage diagnostic.
7. Reports: record counts by year, missing labels, eligible matured labels, coverage flags, fold dates, event prevalence, versioned artifact hashes.

## Important limitation
The current `label_decision` helper returns `negative_requires_coverage_qa` with outcome=0 if its 336h horizon is mature and no hit appears among supplied rows. **Never interpret that outcome as an admissible negative without an independently verified complete trade feed.** Positive hits also need anomaly checks.

## Next execution
Run `python -m unittest research.top_risk_radar_v1.test_label_events -v` in a controlled checkout of the exact research branch and record Python version, SHA, command, exit code, test count, and output. No such run is asserted here.
