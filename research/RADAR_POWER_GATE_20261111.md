# Radar V1 — statistical power gate before further integration (2026-11-11)

Status: [P] analytic memo only (Wilson 95 % intervals). [S] No market data downloaded, no model fit,
no performance run. PAPER only. Base: `research/xrp-top-risk-radar-v1-20261108` @ `d9aa914`
(428 passed locally, Python 3.12).

## Input (already documented, not recomputed)
2022–2025 census run 42427245086 (SHA 8d38fb2): 22 anchored risk episodes (−20 %/14 d) and
16 anchored growth episodes (+30 %/30 d); hourly-close definition, descriptive only
(`research/RADAR_TECHNICAL_REVIEW_20261111.md`). OOS years in PROTOCOL.md: 2022–2026 ⇒ roughly the same
episode count is all the OOS evidence the protocol can ever have.

## Episode-level uncertainty if a model hit the acceptance targets exactly
| Set | episodes | recall 50 % → 95 % CI | precision 60 % (same n alerts) → 95 % CI |
|---|---|---|---|
| Risk 2022–2025 pooled | 22 | 0.31–0.69 | 0.39–0.77 |
| Growth 2022–2025 pooled | 16 | 0.28–0.72 | 0.39–0.82 |
| Risk, one fold (~6) | 6 | 0.19–0.81 | 0.30–0.90 |
| Growth, one fold (~4) | 4 | 0.15–0.85 | 0.15–0.85 |

±10 pp around 60 % needs ≈ 88 independent episodes.

## Consequence
With the current target and single-asset universe, the protocol's acceptance criteria
(precision ≥ 60 %, recall ≥ 50 %, per-year consistency) **cannot be confirmed or refuted at episode
level**; the most likely honest verdict of a correct pipeline is INCONCLUSIVE. Daily metrics
(Brier/log loss vs B0–B2) carry more information but overlap heavily (effective n ≈ episodes).

## Options (decision before more QA effort; none changes a result already seen)
1. Accept V1 as a *diagnostic* (Brier/log-loss skill vs B0–B2 with block bootstrap) and drop the
   precision/recall headline as a pass criterion — pre-registered now, before any performance run.
2. Pre-register a pooled multi-asset version (same targets, PIT universe of liquid Binance spot
   pairs) to reach ≥ 88 episodes — new protocol, needs PIT universe membership.
3. Stop radar development at "technical pipeline done" and spend effort elsewhere.
