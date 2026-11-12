# Radar V1 — G1 decision gate draft (PAPER, NOT APPROVED / NOT RUN)

Status: [P] documented proposal, [S] no performance execution. Date: 2026-11-12. This is **not** a replacement for `research/top_risk_radar_v1/PROTOCOL.md`, and does not grant approval. Scope: Early Growth +30%/30d and Top Risk −20%/14d; decisions must be separate by target. No deployment, merge or live trading.

## Why this gate exists
The archived historical power review cited in dialogue 0315 (Claude: 22 risk and 16 growth episodes in 2022–2025; original source to be independently verified before approval) suggests an episode-level precision claim may be underpowered. Daily rows overlap and are not independent observations. A synthetic passing CI or positive synthetic skill is not predictive evidence. The aim is a single falsifiable, cost-bounded information-value check **if and only if separately authorized**.

## Preconditions G0 (no performance computation)
- Versioned PIT feature bundle bound to each prediction and its SHA-256; verify as-of timestamps, publication/receipt lags, provider continuity, label maturity and perturbation of future inputs leaves historical predictions unchanged.
- Freeze code SHA, raw data SHA, fold boundaries, universe, target-specific horizons, model specification, baselines, hyperparameters, exclusion and missingness rules, bootstrap algorithm and random seed **before** any OOS performance evaluation.
- Tests for null/early-hit labels, train-only fitting, purge/embargo, no oracle synthetic probabilities in empirical data, deterministic artifact serialization and CI exact SHA.
- A dataset inventory and effective independent event/block count computed without inspecting model skill. Insufficient coverage yields INCONCLUSIVE_LOW_N before any performance metrics.

## G1 candidate comparison (proposed; subject to independent review and owner authorization)
- Candidate B3: regularized logistic regression on PIT Model-A features, fitted on train only with chronologically nested parameter selection; no tuning on held-out outcomes.
- Reference: the **best** of M0 (train-only prevalence), B1 (trailing realized volatility) and B2 (returns/drawdown), selected using train-only validation, not the final OOS sample. Compare on exactly identical eligible rows/folds.
- Target-specific walk-forward OOS folds, expanding train, horizon-specific purge and embargo >= 14 days (risk) / >= 30 days (growth), plus publication lag. Do not pool targets when deciding GO.
- Primary: Brier skill score = 1 − Brier(B3)/Brier(reference), on pooled eligible OOS daily rows; uncertainty via moving-block bootstrap of time-ordered data with blocks >= horizon, and sensitivity at 2× horizon. Document calendar blocking, fold stratification and effective sample size. No IID episode bootstrap for empirical GO.
- Secondary, descriptive: log loss, reliability/calibration, episode-level precision/recall, lead time and false alarm episodes/month. Existing PROTOCOL.md proposed alert acceptance (precision >=60%, recall >=50%, <=2 false episodes/month) remains applicable and must be reconciled explicitly *before* the G1 run; do not silently weaken it.
- Proposed GO: point BSS >= 0.05; lower bound of 95% CI > 0 at both block lengths; positive BSS in >=2/3 evaluable folds; and no violation of the frozen alert/calibration acceptance criteria.
- Proposed NO-GO: BSS <= 0 or upper 95% CI < 0.02 at either block length (provided adequate N and valid pipeline). All other outcomes INCONCLUSIVE. These numerical thresholds are **proposals**, not empirically calibrated and must be reviewed for error rates/multiple comparisons before freezing.
- Pre-performance LOW_N: fewer than 30 effective nonoverlapping horizon blocks **or** fewer than 20 positive independent outcome episodes in OOS => INCONCLUSIVE_LOW_N; do not compute or advertise skill as evidence. Counting positives may use outcome census but not candidate predictions. Define effective blocks/episodes deterministically before evaluation.
- G1 is a one-shot pre-registered test. No post-hoc parameter, threshold, feature, data-period or fold selection. Reopening requires genuinely new independently collected evidence and a new protocol.

## Stop rule and resource budget
GO: only then propose a distinct, explicitly approved G2 economic test with executable entry/exit, fees, spread, slippage, turnover, risk and drawdown; radar skill does not imply profit. NO-GO: archive radar development. INCONCLUSIVE or INCONCLUSIVE_LOW_N: **also pause/archive further radar development under this budget**, but report 'not demonstrated', not 'disproved'. A new independent dataset/owner decision is required to reopen.
Budget proposal: at most three deliverables (this protocol appendix; P4 PIT binding + block-bootstrap QA; one separately approved G1 evaluation) or seven calendar days from owner acceptance, whichever first; no new paid infrastructure. The clock does **not** constitute permission to run G1. If authorization is not granted, stop at G0 and report blocked.
Forward PAPER 60–90 days is not a mandatory waiting period for the first G1 decision; it cannot by itself supply enough independent crash/growth episodes. G2 economic execution may require forward PAPER observations under a separately approved protocol.

## Evidence and approval
- [P] This draft is documentation only, created in the isolated radar research branch.
- [S] No new unit tests or performance tests executed by this document.
- References: `research/top_risk_radar_v1/PROTOCOL.md`; dialogue messages 0313 and 0315; archived hypothesis inventory and strategy registry on `research/autopilot`.
- Required owner decision before G1 performance: explicit approval scoped to `výkonnost radar V1 G1`, recorded by the owner through authorized process; this draft is not that approval.
