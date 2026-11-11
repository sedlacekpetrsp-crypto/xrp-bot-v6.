# Radar calibration API divergence — technical blocker (2026-11-11)

[P] Read-only comparison of `research/top_risk_radar_v1/calibration.py` and `calibration_metrics.py` on research branch `research/xrp-top-risk-radar-v1-20261108` (head before this document: `0c804074b1c314d9a424eb9666ec20d415aefc84`).

## Reproducible contract mismatch (code inspection, not executed)

- `calibration.calibration_metrics([(0.0, True)])` clips to 1e-15 and returns finite log loss; `calibration_metrics.log_loss([0.0], [1])` returns positive infinity. Neither behavior is universally wrong, but they **cannot be silently interchanged** when reporting OOS log loss.
- `calibration.calibration_metrics` requires Boolean observed labels; `calibration_metrics._validated` requires exact integer 0/1. The same raw labels fail one API.
- `calibration.calibration_metrics` includes all bins including empty bins and restricts 2–100; `calibration_metrics.calibration_bins` omits empty bins and permits >100. A consumer assuming the same schema can misreport coverage or reliability.
- Both functions are diagnostic primitives, not integrated with a matured-label, PIT-filtered, common-date OOS evaluation pipeline. No predictive claim follows from unit CI.

## Proposed next permitted work [N]

1. Freeze one canonical public scoring contract before integration: label type, infinite-vs-clipped log-loss policy (including explicit clipping epsilon), empty-bin representation, max bins, and abstention/censor handling. Retain a separate explicitly named legacy adapter only if necessary.
2. Add synthetic cross-API conformance tests that assert either identical semantics after explicit adaptation or intentional documented differences; cover p=0/1 with opposite labels, bool/int labels, empty bins, and bins>100.
3. Require the evaluation pipeline to report exact scoring version and number of excluded immature/PIT-invalid observations, with no implicit coercion of unknown labels to negatives.
4. Obtain independent review and exact-SHA CI after any code change; do not fit/calibrate or run performance tests until explicit authorization and data gates.

[S] No tests executed for this document; this is source-level review only. No market data, backtest, model fit, merge, deploy, Render or LIVE.

## Resolution 2026-11-12 (Claude, P1 of DELIVERY-01, dialog 0295/0296)
[P] Single canonical contract `research/top_risk_radar_v1/calibration_metrics.py`, `SCORING_VERSION = "radar-scoring-v1"`:
int 0/1 labels only (bool rejected), `log_loss(eps=None)` = +inf on false certainty, explicit `eps` in (0, 0.5) clips and is
reported by `score()`; all bins returned (empty: count 0, None means), 2–100 bins; `brier_skill_score` for P0-1.
`calibration.py`, `calibration_diagnostics.py` and their 10 test files deleted (no non-test consumer, grep 0).
[S] Locally (Python 3.12): calibration tests 134 → 44; radar suites 428 passed/79 subtests → 338 passed/20 subtests.
Exact-SHA CI and independent review (ChatGPT) pending. No market data, fit, backtest, merge or deploy.
