# XRP Early Growth Radar V1 — preregistration draft
Status: PROPOSED, NOT IMPLEMENTED, NOT RUN. 2026-11-08. PAPER only.

## Purpose
Determine whether point-in-time combinations of XRP/BTC relative strength, spot liquidity, volume, whale/exchange flows, derivatives, retail attention, and verifiable institutional demand predict major XRP spot appreciation better than price/volatility-only baselines.

## Primary outcome proposal
Daily decision at 00:05 UTC, first eligible XRPUSDT spot trade within 60 seconds as P(t).
Y=1 if any eligible spot trade in (t,t+30 days] reaches >=1.30*P(t). Report time-to-first-hit.
For symmetric comparisons also evaluate adverse excursion (minimum future price) and max drawdown before hit. A brief upside wick is not proof of an actionable profitable entry; add robustness using sustained 1h VWAP threshold and independent price source as pre-registered secondary outcomes.
Do not treat this 30-day +30% target as already agreed or empirically optimal. Lock it before performance testing.

## Candidate predictors
A: trailing XRP and BTC spot returns, XRP/BTC, spot volume percentile, realized volatility, trend/drawdown, order-book depth if true point-in-time snapshots exist.
B: funding, OI and liquidations when historically available with as-of timestamps.
C: whale exchange flows, exchange balances, ETF holdings/flows, retail interest, official institutional adoption only with demonstrable publication-time history. Missing historical point-in-time data => exclude, not reconstruct with current labels.
Compare nested A, A+B, A+B+C on identical dates for claims of incremental value.

## Validation
Same 2018-2026 chronological expanding walk-forward as Top Risk Radar, but purge and embargo >=30 days for 30-day labels, adjusted for any longer feature/data lag. Nested time-series calibration and threshold selection only on training data. 2026 last 30 days cannot be evaluated as negative. Overlapping daily outcomes must not be treated as independent events; report 30-day episode metrics and >=30-day block bootstrap uncertainty.
Baselines: event prevalence, trailing realized volatility, momentum/trend, regularized logistic regression on price-only features.
Metrics: precision, recall, PR-AUC, Brier, log loss, calibration, lead time, alerts/month, false alert episodes/month; report annual and regime breakdown, base prevalence and uncertainty intervals.
Predefine both hit-rate and adverse excursion; do not claim trading profitability from threshold-hit classification. Any trade simulation needs separate pre-registered fees, spread, slippage, execution and stop/exit rules.

## Research questions to resolve before test
1. Is +30% within 30 days a useful, non-cherry-picked target, or should event thresholds be based on ex-ante volatility? Compare secondary horizons 14/60 days only if preregistered.
2. How much advance notice is needed for an actionable alert (24h/72h/7d)?
3. Does XRP/BTC improve over XRPUSD and BTCUSD baselines out of sample?
4. Are order-book and exchange-balance signals genuinely timestamped point-in-time?
5. Are whale and ETF indicators predictive after controlling for volatility, trend and BTC?
6. How to avoid a single bull cycle dominating validation?
7. How to separate early-growth alerts from simultaneous top-risk alerts, including a neutral/uncertain state?

## Safety / execution
No LIVE, Render, production, merge, force push. Do not run performance backtest without data QA, frozen protocol and owner approval consistent with dialog/OWNER_DECISIONS.md.
