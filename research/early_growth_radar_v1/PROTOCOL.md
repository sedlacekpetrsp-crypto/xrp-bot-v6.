# XRP Early Growth Radar V1 — proposed protocol (not validated)

Status: [P] protocol only; [S] no performance test, historical model fit, forward alerts or deployment.
PAPER research, isolated branch research/xrp-top-risk-radar-v1-20261108.
This is a **different prediction target** from the 14-day downside radar; do not treat a descriptive census as OOS evidence.

## Frozen target proposal (subject to independent review before model evaluation)
- Universe: XRPUSDT spot on a declared single venue; daily UTC decision at 00:05.
- Decision reference: first eligible spot trade at/after decision, within 60 seconds; otherwise abstain and log missingness.
- Label positive if any eligible trade price in (decision, decision+720h] >= 1.30 × reference. Retain first_hit_at.
- A negative label is mature only after 720h; at the cutoff, censor the last 30 days, never call them negative.
- Validate anomalous wicks via predeclared cross-feed QA; retain raw and filtered outcomes with reasons.
- The target describes an **upside touch**, not an executable +30% realized trade return. No performance or profit claim.

## PIT contract and leakage barriers
- For every feature: event_time, source_published_at, collector_received_at, decision_time, dataset_version, checksum.
- Require event_time < decision_time and both publication/receipt <= decision_time. Missing timestamps fail closed.
- Revisions and retrospectively labeled exchange wallets must not be used as if known historically.
- No current top-performing tokens selection, future volatility, hindsight regime labels, future constituent data or final-period tuning.
- Overlapping 30-day labels require >=30-day train/test purge; apply embargo for relevant feature windows and publication lag.
- Fit scaling, missingness handling, feature selection, calibration and alert thresholds **only inside chronological training folds**.

## Baselines and falsification
- B0 expanding-window event frequency; B1 trailing XRP realized volatility; B2 7/30-day return and drawdown; B3 regularized logistic on XRP/BTC past-only OHLCV.
- Hypothesis: pre-event spot volume expansion plus XRP/BTC relative strength improves calibrated 30-day upside-touch probability beyond B0–B3.
- Negative controls: shift feature timestamps into the future (MUST trigger leakage guard), shuffle labels within training folds (MUST destroy any supposed edge), and compare against volatility-only.
- Evaluate walk-forward PR-AUC, Brier, log loss, reliability by fold/year, alert episode precision/recall, coverage and lead time; uncertainty with >=30-day blocks. No metric computed in this protocol-only commit.
- No OOS candidate promotion without independent locked holdout and >=90 days immutable forward PAPER observation.

## First implementation gates
1. Reuse the fail-closed timestamp guard from research/top_risk_radar_v1/pit_guard.py; 720h label maturity for this target.
2. Define canonical trades schema, QA for duplicate IDs, missing periods, zero volume, venue changes and outlier prints.
3. Produce a data manifest with hashes, start/end, retrieval date and source-lag evidence before any historical evaluation.
4. Obtain independent review of target, splits and false-positive costs. A descriptive historical census may be useful for prevalence, but is NOT predictive validation.

## Decisions and restrictions
No LIVE, Render, production, merge, force push, model-performance run or data download performed here. Do not represent this document as an implemented radar.
