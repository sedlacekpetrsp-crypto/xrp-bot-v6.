# XRP Radar V1 — immutable baseline and dataset build specification
Status: PROPOSED, NOT RUN. PAPER only. 2026-11-08.

## Source hierarchy and exclusions
Primary XRP/USDT spot: exchange-native historical trades with verified event timestamps, symbol and venue, source file checksums and continuity. Secondary independent price feed for spot-checking spikes and outages. Never substitute OHLC highs/lows for first eligible trade reference without an explicitly versioned alternate target.
If only candle data are available, create a separate candle-based research protocol and do not report it as the trade-level protocol.
BTC/USDT and XRP/BTC spot history: same time basis, venue metadata and independently documented gaps.
Derivatives, on-chain whale tags, exchange balances, ETF flow data, retail attention and institutional announcements are optional until historical publication timestamps can be demonstrated. Exclude rather than backfill revised or current classifications into the past.
Never put raw exchange API credentials or proprietary data into the repository.

## Data manifest schema (one record per source/version)
- source_id, provider, market_type, venue, symbol, timezone
- start_utc, end_utc, event_timestamp_field, published_timestamp_field, received_timestamp_field
- granularity, acquisition_utc, raw_sha256, row_count
- missing_intervals, duplicate_policy, correction_policy, anomalies_reviewed
- license_or_terms, provenance_url, point_in_time_supported, qa_owner, qa_status

## Baseline features (computed only with past observations)
At decision 00:05 UTC:
- XRPUSD log returns: 1d, 7d, 30d
- BTCUSD log returns: 1d, 7d, 30d
- XRP/BTC relative return 1d, 7d, 30d
- XRPUSD realized volatility: trailing 7d, 30d
- XRPUSD rolling drawdown: trailing 30d
- spot volume z-score / percentile: trailing 30d, if genuine PIT
All rolling calculations must use data available strictly before the decision. For candles, a candle ending at 00:05 cannot be used unless fully closed and received by then. Do not silently forward-fill across outages.

## Comparator hierarchy
M0: historical base-rate per training fold (constant probability).
M1: XRPUSD past returns + volatility.
M2: M1 + BTCUSD returns and XRP/BTC relative strength.
M3: M2 + PIT spot volume/depth.
M4: M3 + PIT derivatives.
M5: M4 + PIT whale/on-chain/ETF/retail/institutional signals.
Use logistic regression with training-only regularization/calibration and common evaluation dates; if an added feature family reduces comparable dates, rerun both models on the intersection before claiming incremental value.
Report ablations and uncertainty intervals, not just best fold.

## Split schedule
Expanding training 2018–2021 -> test 2022; then train through 2022 -> test 2023; through 2023 -> test 2024; through 2024 -> test 2025; through 2025 -> test 2026. These splits require sufficient actual data and positive events; do not silently claim all years available.
Purge/embargo: >=14 days downside, >=30 days growth, >=30 days joint. Remove unresolved label windows at fold edges and at current as-of. Calibrate and select alert thresholds only within training. Group correlated daily signals into episodes and bootstrap blocks >=30d.

## Metrics
Downside and growth separately: event prevalence, precision, recall, PR-AUC, Brier score, log loss, calibration by probability bin, median lead time and lead-time percentiles, false alerts/30d, annual fold outcomes, episode-level metrics. Bootstrap 95% intervals. Report abstentions and data insufficiency.
A claimed improvement requires positive out-of-sample difference versus M1/M2 with uncertainty and consistency across years. Do not imply causal benefit or realizable trading profit.

## Execution gate
1. Inventory and acquire sources lawfully.
2. Create source manifest with real checksums.
3. Audit coverage and independent source agreement.
4. Freeze data snapshot, labels, features, splits, metrics, and seeds.
5. Run only approved PAPER research and publish reproducible results.
No LIVE, Render, production merge, trading execution, or invented performance numbers.
