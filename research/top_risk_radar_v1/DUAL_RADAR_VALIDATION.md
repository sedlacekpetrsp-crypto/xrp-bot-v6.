# Dual XRP Radar V1 — joint-outcome and conflict protocol
Status: PROPOSED / NOT RUN. 2026-11-08. PAPER research only.

## Objective
Determine whether two independently trained and calibrated probability estimates provide decision-useful *early* warning:
- Growth: +30% XRPUSDT spot threshold within 30 days.
- Downside: -20% XRPUSDT spot threshold within 14 days.
These events are NOT mutually exclusive. Never define downside as 1-growth or vice versa.

## Joint outcomes and path dependency
For each UTC 00:05 decision, use same venue and eligible reference trade for both radars.
Record growth_hit_at, downside_hit_at, first_event, max favorable excursion (MFE), max adverse excursion (MAE), and maximum drawdown before growth hit.
Possible labels: neither; growth only; downside only; both (growth first); both (downside first). Both events may occur in one 30-day window. The downside 14-day window is shorter and must not be conflated with 30-day growth window.
Report hit before adverse excursion, not only maximum high and low. A +30% wick is not a simulated profitable trade.

## Proposed diagnostic categories (NOT trading orders)
- GROWTH_WATCH: growth probability exceeds a training-only threshold while downside risk is below its separately calibrated training-only threshold.
- RISK_WATCH: downside risk exceeds its threshold.
- CONFLICT: both probabilities exceed their respective thresholds. Never silently suppress one.
- NEUTRAL: neither exceeds its threshold.
- DATA_INSUFFICIENT: missing/unreliable as-of inputs or uncalibrated distribution shift.
No claims of actual probabilities or thresholds until trained and validated. Conflict is not a buy/sell instruction.

## Tests that can falsify value
1. Compare each radar against price/volatility-only and BTC-conditioned baselines on identical timestamps.
2. Remove each feature family (whale, derivatives, liquidity, retail, institutional) one at a time; report incremental OOS PR-AUC and Brier differences with block bootstrap uncertainty.
3. Time-shift each nonprice feature *backward* beyond its publication delay (valid lag) and separately use an impossible future shift as a leakage diagnostic; any implausible improvement requires investigation, not publication as performance.
4. Negative control: shuffle signal values within training-year blocks (preserving approximate regime distribution) and repeat pipeline. Real model should exceed controls on untouched OOS.
5. Stratify by BTC regime and volatility; verify gain isn't merely detecting generalized crypto stress.
6. Evaluate signal lead-time at >=24h, >=72h and >=7d before threshold crossing; exclude alerts occurring after an event is already underway from 'early' headline metrics.
7. Verify reproducibility with source hashes, immutable cutoff, per-year metrics and fully specified seeds.

## Temporal validation
Separate horizon-specific purging: >=30 days for growth, >=14 days for downside; when evaluating joint outcomes use >=30 days plus source publication lags. Evaluate only fully matured 30-day windows for joint-negative outcomes.
Avoid sample leakage from feature normalization, calibration, thresholds, regime labeling and retrospective address tags.
Daily samples overlap. Publish both daily and de-duplicated episode-level metrics, with uncertainty via blocks >=30 days.

## Acceptance decision
A convincing system must beat prespecified baselines OOS, be calibrated, provide actionable lead time, and survive at least 90 days immutable forward PAPER observation. Do not interpret historical price threshold classification as realized P&L. No automated trading or Render deploy.

## Work order
1. Independent Claude review of both radar protocols.
2. Data-source availability / as-of audit and trade-coverage QA.
3. Unit tests of target labels, especially both-event ordering and end-window boundaries.
4. Frozen baseline + threshold protocol.
5. Owner-approved performance run if all gates pass.
