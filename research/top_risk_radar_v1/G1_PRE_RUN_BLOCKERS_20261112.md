# Top Risk Radar G1 — pre-run blocker register (2026-11-12)

Status: **NOT FROZEN / NOT EXECUTED**. PAPER research only. This document is a preflight checklist, not an authorization to run performance or a replacement for `PROTOCOL.md`.

## Evidence reviewed
- `PROTOCOL.md`: 00:05 UTC decision, first eligible trade at/after 00:05 within 60 s; positive label requires a subsequent trade at or below 80% of reference price.
- `test_trade_identity_integration.py`: synthetic same-timestamp trade-ID ordering and exclusion of ties at the exact decision boundary.
- GitHub Actions 43285501867 (SHA `51fd44310c7a4b46c2c23a602278d0fef6ac8efb`) and 43285524576 (SHA `990a083029b11e933cdc3133705c3565af863d44`): both completed/success; **these are unit/CI evidence, not G1 performance evidence**.
- Dialog 0324 (Claude draft `G1_FREEZE_MANIFEST_DRAFT_20261112.md`, commits `6746c02`/`a27831b`) and independent review 0326.
- Owner approved **one** historical PAPER G1 performance test in chat 2026-11-12, conditioned on freezing protocol, data and decision criteria; no merge/deploy/LIVE. `dialog/README.md` separately requires an owner authorization row in `dialog/OWNER_DECISIONS.md`; the owner explicitly forbids this assistant from editing that file.

## Hard gates — all must be closed before the single G1 run

1. **PIT reference and target consistency.** Preserve original tick/trade-level rule from `PROTOCOL.md`, or explicitly register a methodological deviation *before* observing predictions. Do not silently substitute 00:05 minute OPEN at decision_at=00:05. The 00:05 candle can contain its first trade later than decision time; the candle LOW can precede the selected reference trade. Require exchange trade ID and timestamp ordering for all same-timestamp comparisons. Test delayed first trade, trade-free minute, early LOW before reference, exact horizon boundary, missing minute, tied timestamps with and without identity.
2. **Mature labels / embargo.** Every training outcome must have a complete 336 h horizon at its training cutoff, including early-hit positives. Purge any training label interval that overlaps OOS and apply at least 14 d embargo. No label maturity inferred from knowing a future early hit.
3. **Immutable data manifest.** Freeze source, symbol, venue, time range, exact archive names and SHA-256, `.CHECKSUM` verification, timestamp units, trade IDs, XRP/BTC cross-source coverage, missing/duplicate minute, zero-trade bars, price anomalies and excluded decisions. A checksum of a ZIP alone is not a continuity audit. Any mismatch => INVALID_RUN.
4. **Immutable code and splits.** Pin full commit SHAs for loader, feature generation, labels, models, runner, protocol and dependency lock. Define exact chronological folds and inner training-only validation. No adjustment of folds after observing results.
5. **Fixed competitors and scoring.** Predefine M0/B1/B2 and candidate B3, selection exclusively on earlier training folds, all hyperparameters, alert budget, Brier/log loss, calibration and episode metrics. Explicitly handle 0 denominators, invalid CI, ties, missing scores and baseline selection. No post-hoc threshold tuning.
6. **Uncertainty / sample sufficiency.** Predefine 14 d and 28 d within-fold moving-block bootstrap, 2000 replicates, seed 20261112, episode counts and positive events by OOS fold. Fewer than three evaluatable folds => INCONCLUSIVE. The historical census of 21 clustered risk events is not 21 OOS events; mark `LOW_N_MARGIN_POST_HOC_GATE`. No confirmed predictive skill or profitability follows from the census.
7. **Single-run operational lock.** Performance runner must be manual-only with immutable SHA, explicit confirmation token, no schedule, no retry, bounded resource cost and reproducible output artifacts. Unit/synthetic CI must not invoke performance code. No exploratory real-prediction runs prior to freeze.
8. **Owner authorization gate.** Before execution verify the exact applicable `SCHVÁLENO: výkonnost radar V1 G1` authorization in `dialog/OWNER_DECISIONS.md` as required by `dialog/README.md`. **Do not modify OWNER_DECISIONS.md** under the current owner instruction. The chat approval does not waive the repository gate.

## Outcome rules
- **INVALID_RUN:** broken data hash/coverage, PIT violation, wrong code/protocol, unauthorized or repeated performance run, invalid scoring.
- **INCONCLUSIVE:** fewer than three evaluatable OOS folds, insufficient positive episodes for meaningful inference, contradictory/undefined confidence intervals or otherwise inconclusive evidence.
- **NO-GO:** valid but fails the frozen G1 decision criteria.
- **GO (research only):** passes all frozen G1 screening criteria; requires further independent validation and does not imply profitability, a deploy, or candidate status.
- Freeze all quantitative decision thresholds and precedence in the final manifest **before** the run. This register deliberately does not invent unreviewed thresholds.

## Execution record
[P] Documented blocking conditions and reconciled the primary trade-level protocol against the 00:05-minute-candle draft.
[S] No performance backtest, data G0 execution, local tests, merge, deploy, Render, LIVE or production changes. CI statuses above were read-only verified.

## 2026-11-13 preflight integration audit (no performance execution)

Verified on the research branch: `g1_preflight.complete_g1_folds` composes
`require_complete_g1_decision_days`, `validate_g1_decisions`, and
`g1_calendar_folds`. The last function fixes a 14-day label horizon and
an **additional** 14-day embargo. These functions are deterministic calendar
QA only; they do not fetch, inspect or verify market trades.

**Critical distinction: calendar completeness is not source completeness.**
Passing `complete_g1_folds` demonstrates only that supplied daily 00:05 UTC
*decision timestamps* cover the caller-declared inclusive bounds. It does NOT
establish that the caller declared the entire frozen observation period, that
underlying trades exist within the required 60-second reference window, that
future trades cover all 336 hours, that archive hashes and trade identities
are correct, or that PIT feature publication timestamps precede decisions.
An attacker or buggy loader could fabricate a perfect daily decision grid from
an incomplete trade archive and pass this gate. Treat such a result as
**NOT DATA-QA-PASSED** until independent source checks are attached.

Before any G1 runner may execute, require the following *separate* evidence:

- Coverage bounds come from the frozen dataset manifest, never from the
  observed first/last decision rows. The manifest must explicitly enumerate
  expected train and OOS calendar periods and exclusions.
- For every included decision, record first eligible reference trade's
  timestamp, unique trade ID, price and source checksum; exclude and count
  decisions without an eligible trade in [00:05:00, 00:06:00) UTC.
- Verify chronological trade ordering for every label hit; same-timestamp
  ties must be resolved using exchange trade IDs. Report missing archives,
  duplicate IDs, timestamp-unit mismatches, archive continuity and price
  anomalies separately from daily decision-grid coverage.
- Freeze and independently inspect each feature's `source_published_at` and
  `collector_received_at` before allowing it into a decision; no imputed
  publication times or revised future values without a pre-registered rule.
- The eventual G1 runner must call `complete_g1_folds` **and** the distinct
  trade/PIT/data-manifest gates, then produce an auditable fail-closed receipt
  before the single owner-authorized performance run. This integration is
  **NOT IMPLEMENTED** as of this audit; tests of individual helpers do not
  establish it.

[P] Read-only inspected the preflight, calendar coverage and fold contract;
recorded their actual limits and the required runner-level gate wiring.
[S] No new test executed and no performance backtest executed. Prior CI success
for calendar-only unit tests must not be interpreted as trade-level validation.
