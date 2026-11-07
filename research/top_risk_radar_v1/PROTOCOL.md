# XRP Top Risk Radar V1 — pre-registered research protocol
Status: PROPOSED / NOT RUN. PAPER only. Created 2026-11-08.
Scope: predictive risk of XRP/USDT spot declining >=20% from signal-time reference price within the following 336 hours. No live trading, deployment, merge, or Render changes.

## Target and timestamp
- UTC decision time daily 00:05:00.
- Reference price P(t): first eligible XRPUSDT spot trade at/after decision time, within 60 seconds; missing => exclude with reason. Never use candle close before signal as executable price.
- Positive label: at least one eligible XRPUSDT spot trade with price <=0.8*P(t) in (decision_time, decision_time+336h]. Capture first_hit_at.
- Label matures only after the entire 336-hour horizon unless already hit; evaluation dataset is frozen at a declared cutoff.
- The same venue, price feed, timezone, adjustment and outage rules must be used for P(t) and future price. Mark anomalous prints and verify against independent market source; pre-register exclusion rule before observing outcomes.
- Keep a secondary daily-low label for diagnostics only, not the primary result.

## Data as-of contract
For every observation retain event_time, source_published_at, collector_received_at, decision_time, provider, dataset_version, quality_flag, and original payload checksum.
An input is eligible only if max(source_published_at, collector_received_at) <= decision_time. If published_at unavailable, apply documented conservative lag; otherwise omit.
No current exchange wallet labels projected backwards. Revisions, delistings, survivorship and API outages must be versioned.
Feature computation must use only matured, point-in-time records. Feature windows stop strictly before decision time.

## Two models
A (mandatory): historical XRP and BTC spot OHLCV/trades, XRP/BTC relative strength, realized volatility, returns, drawdown, spot aggressor volume if available. Funding and OI only after their reliable historical start date, with a missingness indicator or separate evaluation universe.
B (optional): on-chain exchange netflows, whale exchange deposits, realized profits, ETF holdings/flows and public attention, only with provable as-of publication and historical coverage. No backfilled labels.
Compare both on identical timestamps when claiming B adds value.

## Walk-forward
- Earliest candidate history 2018-01-01, subject to data QA. 2017 supplemental only.
- Expanding train: 2018-2021 -> test 2022; 2018-2022 -> test 2023; 2018-2023 -> test 2024; 2018-2024 -> test 2025; 2018-2025 -> test 2026 through last matured label.
- Purge training samples whose 336h label interval touches the test interval. Apply >=14-day embargo and respect feature-publication lags.
- All scaling, imputation, feature selection, calibration, hyperparameters and alert thresholds fitted on earlier training data using nested chronological splits.
- Lock protocol, code revision and data hashes before final holdout. Do not retune on holdout results.

## Baselines
B0 historical positive event frequency; B1 trailing realized volatility; B2 7/30-day returns + drawdown; B3 regularized logistic regression on Model A. Candidate radar must exceed these on OOS evidence.

## Evaluation
Daily: TP,FP,FN,TN at frozen training-selected threshold; precision=TP/(TP+FP), recall=TP/(TP+FN), PR-AUC, Brier score, log loss, reliability curve, calibration slope/intercept, base event rate.
Episode level: consolidate adjacent alerts into pre-defined 14-day risk episodes; measure event precision, event recall, false episodes per month and lead time. Do not count overlapping daily labels as independent evidence. Use chronological block bootstrap with blocks >=14 days for uncertainty.
Report by year, bull/bear/sideways regime (regime defined using only past data), missing-data coverage, and venue outages.
Compare to base-rate and baselines with uncertainty intervals, not only point estimates.

## Proposed research acceptance criteria (NOT achieved)
Precision >=60%; recall >=50%; <=2 false alert episodes/month on OOS; Brier better than all baselines; acceptable calibration; >=90 days immutable forward PAPER observations.
If class prevalence makes targets unattainable, report failure transparently; do not change thresholds after seeing final results.

## Data quality gates
- Verify continuous minute/trade coverage, duplicate/missing timestamps, timezone, price spikes, volume units and instrument mapping.
- Report exact available start/end per source and publication lag.
- Verify labels manually for a sample of positive, negative and borderline events.
- Exclude last 14 days from matured-negative evaluation.
- No performance run until approved protocol/data gates are documented and owner authorization is confirmed as applicable.

## Required artifacts
manifest.json (dataset hashes and time spans), data_qa.md, predictions.csv (one row per signal), episodes.csv, metrics_by_fold.csv, calibration plots, baselines.csv, false_positives.md, missed_crashes.md, reproducible command log.
All outputs must distinguish PROPOSED, IMPLEMENTED and EXECUTED. No profit claim or candidate promotion from backtests alone.
