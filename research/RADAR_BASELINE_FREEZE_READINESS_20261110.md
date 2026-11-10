# Radar V1 — baseline freeze readiness and CI verification gate (2026-11-10)

Status: [P] documentation/QA checklist only. [S] No performance backtest, calibration fit, forward prediction, data download or deploy executed in this change. PAPER research only.

Applies to `research/early_growth_radar_v1/PROTOCOL.md` (+30% touch in 720 h) and `research/top_risk_radar_v1/PROTOCOL.md` (-20% touch in 336 h). **Historical event census is descriptive, not predictive OOS validation.**

## Gate 0 — CI integrity
- Workflow: `.github/workflows/xrp-radar-unit-tests.yml`, triggered on relevant Python changes on this branch; docs-only commits do not trigger it.
- For a green result, record **run URL, run ID, commit SHA, event, branch, conclusion, number of tests and failed/skipped counts**. A successful run on an earlier SHA is not proof for a later code revision.
- A GitHub API lookup that only returns PR-triggered runs cannot establish whether push-triggered CI ran. Record verification as UNKNOWN until an appropriate Actions run is inspected.
- The workflow compiles both radar modules and runs deterministic pytest with pinned pytest 8.3.3; it is not a predictive performance test.
- CI red or missing on the tested code SHA => no technical completion claim.

## Gate 1 — point-in-time data and labels
- Strict feature admissibility: event_time < decision_time, source_published_at <= decision_time and collector_received_at <= decision_time; missing provenance => abstain.
- Preserve original payload hashes, venue/instrument identity, revision history and source publication lag. Never project today's tags, listings or constituents backwards.
- Labels: first eligible spot trade within 60 seconds of 00:05 UTC; +30%/720h or -20%/336h touch is **not** executable profit/loss. Track first_hit_at and anomalous prints separately.
- Censor last 30 days for Early Growth and 14 days for Top Risk; do not silently convert censored examples into negatives.
- Synthetic QA cases: exact decision-time boundary, delayed publication, delayed collector receipt, missing timestamps, revised record, duplicate trades, no eligible reference trade, borderline touch, horizon boundary, immature negative and future feature shift.

## Gate 2 — baseline comparison (not executed)
- Freeze B0 historical event frequency; B1 trailing realized volatility; B2 past-only returns/drawdown; B3 regularized logistic using historical XRP/BTC.
- Keep separate targets and target-specific purges (>=30 d growth, >=14 d downside), with nested chronological train-only preprocessing, calibration and threshold selection.
- Evaluate on identical matured OOS timestamps: Brier, log loss, PR-AUC, fold/year calibration, coverage, episode-level false alarms and lead time. Block uncertainty by at least label horizon; overlapping daily outcomes are dependent.
- No claim of improvement unless candidate beats predeclared baselines with appropriate uncertainty, locked holdout and >=90 days immutable forward PAPER evidence.

## Gate 3 — sector data
- CryptoSector.net, current category tags and paid Datonomy are **not approved PIT inputs**. No scraping or paid procurement.
- A Binance Vision quote-volume basket is **not** BTC market-cap dominance. It must not be labelled BTC.D; historical membership/delistings and as-of availability must be evidenced before any proposed ablation.
- No sector feature is currently added. Complete baseline before any independently preregistered sector ablation.

## Next permitted technical work
Inspect the newest Actions run for the exact radar branch SHA; if failed, isolate and fix deterministic unit/QA failures, recording the real CI evidence. Additional test-only commits are permitted on the isolated research branch. No performance run, merge, deploy, Render, LIVE or force push.
