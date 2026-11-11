# XRP radar V1 — P2 feature/baseline integration acceptance contract
Status: PROPOSED / NOT IMPLEMENTED / NOT PERFORMANCE-TESTED. PAPER only. 2026-11-12 UTC.

Purpose: define a minimal, falsifiable handoff for `features.py` and `baselines.py` before code is written. This is an implementation contract, **not** an OOS or profitability result. It must be reconciled with `BASELINE_DATASET_SPEC.md`, `PROTOCOL.md`, and Claude's P1 canonical calibration contract before integration. No merge or deploy authorized.

## 1. Point-in-time row and source contract
One prediction row per `(target_version, decision_time_utc, fold_id)`, with UTC decision at 00:05. Required provenance for every input: `event_time`, `source_published_at`, `collector_received_at`, `provider`, `dataset_version`, `quality_flag`, `payload_sha256`. Eligible only when event and publication/receipt are demonstrably available **strictly before** decision time; if source lacks trustworthy publication/receipt, exclude or use a separately documented conservative lag. Do not derive availability from the final data-file download time.

For OHLCV: only fully closed, published and received candles may contribute. No forward fill across gaps or outages. Distinguish `missing_source`, `not_yet_published`, `insufficient_lookback`, `quality_excluded` from legitimate numeric zero. Train-only imputation, scaling, and hyperparameter selection; do not fit preprocessing on OOS.

## 2. Feature schema and invariant
Minimal numeric columns from the existing dataset spec:
- XRP and BTC log returns 1d/7d/30d; XRP/BTC relative log returns 1d/7d/30d;
- XRP trailing realized volatility 7d/30d; XRP rolling drawdown 30d;
- optional PIT spot-volume z-score/percentile 30d, **not** silently imputed as zero.

Each feature row records the maximum contributing `event_time` and `available_at=max(published_at, received_at)`; both must precede decision time. Reject duplicate candles, overlapping source versions, timezone-naive timestamps, or discontinuous windows rather than silently using fewer observations. Horizon (336h downside / 720h growth) belongs to the **target/label**, not to historical feature-window availability.

## 3. Baselines and model ownership
Use existing `BASELINE_DATASET_SPEC.md` hierarchy M0–M5, with M0 constant train-fold event frequency. For first integrated milestone implement only M0, M1 (XRP returns + vol), M2 (M1 + BTC and XRP/BTC); later families require independently verified PIT coverage. `PROTOCOL.md` also uses B0–B3 nomenclature: provide an explicit mapping before reporting results; never assume B1–B3 and M1–M3 are identical. Train/test boundaries, purge and embargo are target-specific; joint pipeline uses >=30d. Baseline fitting must be a separate, train-only operation.

## 4. Minimal non-performance QA acceptance
1. Synthetic series with exact, known returns/vol/drawdown yields reproducible feature values.
2. **Future candle injection:** add a candle with event_time or available_at >= decision time; feature output must be unchanged or rejected with an explicit reason. Deliberately shifting a used candle one bar into the future must fail eligibility.
3. **Publication delay:** old event_time with late collector_received_at is excluded.
4. **Outage:** remove a required candle; reject that lookback instead of forward filling.
5. **Fold isolation:** change OOS labels/rows without changing train-fold M0–M2 fit parameters.
6. **Dual-target:** same historical feature inputs can feed either target, but label maturity/exclusions remain horizon-specific.
7. **Serialization:** deterministic row ordering, UTC ISO-8601 timestamps, schema version and stable hash of synthetic output.

## 5. Done definition and review gate
P2 is complete only when the pipeline can import real `features.py` and `baselines.py`, all seven synthetic acceptance checks pass in exact-SHA CI, and an independent reviewer inspects time eligibility and fold isolation. Do not claim a predictive result from synthetic injected-signal tests. P3 later connects source -> PIT features -> folds -> mature labels -> predictions -> canonical scoring with counts for exclusions. Historical data quality and statistical power remain separate blockers.

This file itself executes no tests, reads no market outcomes, and makes no trading recommendation.
