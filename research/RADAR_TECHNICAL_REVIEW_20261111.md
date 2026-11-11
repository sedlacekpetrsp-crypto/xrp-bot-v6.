# Dual XRP radar: technical review handoff, 2026-11-11

Status: IMPLEMENTED + EXECUTED technical QA; independent review PENDING.
Overall technical development INCOMPLETE; predictive reliability UNPROVEN.
PAPER only. No model fit, new performance census, threshold optimization,
LIVE, Render, production change, merge or force push.

## Starting state and deduplication

Inspected radar branch at `1c4aa3552fa06b1c6b7c524089271c56b7abf410`, its
history, both protocols, baseline dataset specification, fold/PIT/calibration
modules, tests, workflow triggers, and dialog README/OWNER_DECISIONS. Read
0223/0224 (closed target review), latest 0282/0283 (unrelated K7 work), and
0274–0276 references concerning sector-data restrictions.

The remembered 54 tests were an older checkpoint. Actual baseline: **359 passed**
locally (Python 3.12, pytest 8.3.3), independently confirmed in CI job
130427838258 on the exact starting SHA:
https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./actions/runs/42992295109
Event push; correct research branch; conclusion success; no failures/skips.

Existing real-data evidence was inspected, not recomputed as a new study:

| Evidence | Verified result | Limitation |
| --- | --- | --- |
| Archive QA run 42426123650, SHA 9821c43efb8230dea1e9dd905871ced831582b1c | 225,913 XRPUSDT trades, 116,198 adjacent equal timestamps, SHA256 verified | Single day; no independent cross-feed or PIT feature verification |
| 2022–2025 census run 42427245086, SHA 8d38fb23916be52336f69fad7476528c5f00108c | 48 archives; 16 anchored growth episodes, 22 anchored risk episodes | 01:00 hourly-close target; overlapping descriptive labels, NOT trade targets or OOS predictions |

Run links:
- https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./actions/runs/42426123650
- https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./actions/runs/42427245086

## Defects repaired and missing implementation added

1. `binance_spot_trades.py` discarded native trade IDs. It now preserves them,
   rejects duplicate/decreasing IDs, invalid quantities/flags and nonfinite
   prices, and converts epochs with integer microseconds. The actual archive
   uses `False,True`; both that spelling and existing lowercase fixtures work.
2. `coverage_qa.py` rejected all timestamp ties, conflicting with real archive
   evidence. Identified contiguous native IDs now distinguish legitimate ties
   from duplicates. Missing, mixed, duplicate or time-inconsistent IDs fail
   the identity check. Anonymous distinct-timestamp legacy fixtures retain
   their explicitly unverified heuristic; they do not prove completeness.
3. Downside labeling previously skipped valid hits sharing the reference's
   timestamp. Native IDs now establish reference order; ambiguous anonymous
   ties raise ValueError. The interval remains **(decision, deadline]**: every
   trade exactly at decision is excluded as a hit, as specified by the protocol.
4. Early Growth had protocol/PIT tests but no trade-level label entrypoint.
   Added its +30%/720h descriptive label using the shared reference machinery.
   Tests cover both-event order, separate 336h/720h horizons, exact thresholds,
   delayed references, future-data exclusion and censorship.

These are raw-touch **data labels**, not probabilities or alerts. Positive
touches are provisional with respect to anomalous-print QA. The caller must
prove venue/symbol consistency and coverage. Mature negative status remains
`negative_requires_coverage_qa`; early positive labels must wait for full
horizon maturity before evaluation to avoid selective inclusion of positives.

## Actually executed verification

- Full deterministic suite: **395 passed**, 0 failures, 0 skips; pytest 8.3.3.
  Baseline 359 + 36 new regression cases. Local Python 3.12.
- Both module trees compiled successfully; `git diff --check` passed.
- Replayed the same known 2024-01-02 archive through the new parser, after
  checksum verification. All **225,913** rows parsed, native IDs
  576925834–577151746 contiguous, **0 missing IDs**.
- Fixed one-minute feed QA at 00:05 UTC: 180 trades, 88 adjacent timestamp
  ties, maximum inter-trade gap 4.835 seconds; passes the declared 5-second
  heuristic with contiguous IDs. This is NOT full 14/30-day coverage.
- First replay exposed an overly narrow lowercase flag check; repaired to
  support the observed archive format, added the actual row as regression,
  and reran successfully. No failed attempt hidden as success.
- Source checksum, source URLs, exact code hashes and replay output are in
  `top_risk_radar_v1/ARCHIVE_REPLAY_20261111.json`.

Commands (from repository root):
```sh
python -m pytest -q research/top_risk_radar_v1 research/early_growth_radar_v1
python -m compileall -q research/top_risk_radar_v1 research/early_growth_radar_v1
python -m research.top_risk_radar_v1.replay_trade_archive
```
The final command explicitly downloads the fixed public archive for QA only;
unit tests perform no downloads. No raw archive is committed. New GitHub CI
must be checked on the resulting commit; baseline CI is not proof of it.

## Independent review request and remaining gates

New topic TRADE-IDENTITY-01, round 1; does not reopen the closed target debate.
Claude should independently inspect ID/time ordering, reference ties, error
paths and target separation, reproduce the tests, and compare the archived
replay evidence with the source hashes. Changes directly affect label and
coverage validity; no redundant PIT or calibration test expansion requested.

This packet is ready for review of these technical changes, **not** approval
of complete radars or a predictive evaluation. Remaining work:

1. Confirm independent technical review and exact-commit CI.
2. Freeze a versioned primary downside target. Dialog 0224 proposes 1min
   close as operational primary and raw touch as descriptive sensitivity;
   the checked owner decisions contain no explicit resolution. Do not
   silently replace the existing raw-touch protocol or start fitting.
3. Build the multi-year trade/minute dataset with independent price QA,
   anomaly policy, PIT provenance and immutable hashes. Existing hourly
   census and one-day replay do not satisfy this gate.
4. Complete the feature/baseline/evaluation pipeline under the frozen target,
   including nested chronological fitting, calibration, label-publication
   lags, common OOS dates, episode uncertainty and untouched holdout.
   Existing helpers are not an integrated forecasting system.
5. Obtain applicable explicit performance authorization after the data and
   protocol gates; then evaluate and observe >=90 days immutable forward
   PAPER. No success/candidate claim now.
