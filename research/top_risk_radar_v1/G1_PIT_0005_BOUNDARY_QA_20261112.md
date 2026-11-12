# G1 pre-freeze QA: 00:05 first-trade PIT boundary

Status: SPECIFICATION ONLY — no performance test, no model output. Independent review of Claude's G1 freeze draft (`a27831b`) and dialog 0324/0326.

## Blocking ambiguity
Draft uses `decision_at=00:05:00 UTC`, `P(t)=OPEN` of the 00:05 one-minute kline and the 00:05 minute's LOW as part of the 14-day label. The 00:05 OPEN may be the first trade **after** 00:05:00 and therefore not observable at exactly decision_at. The 00:05 LOW can be before or after that first trade within the minute; the label must not implicitly use unavailable within-minute order.

## Required freeze choice (must precede any performance run)
- **Trade-time contract:** use actual timestamp of first trade at/after 00:05 and label only subsequent trades in a strictly defined 336h window; require verifiable trade-level data, or
- **Completed-bar contract:** decision_at no earlier than 00:06:00, reference price and label start defined in terms of observable completed bars; document this as a deviation from the 00:05 protocol and freeze before testing.
Do not silently redefine the decision timestamp or choose the variant based on outcome counts.

## Synthetic unit QA cases
1. First trade at 00:05:00.000 exactly: inclusive boundary is deterministic.
2. First trade at 00:05:43: OPEN unavailable at 00:05:00; reject as PIT-unsafe under 00:05 decision contract.
3. No trades in 00:05:00–00:05:59: exclude or follow the explicitly frozen fallback; never forward-fill a future price.
4. LOW at 00:05:02 and first trade timestamp 00:05:43: ensure label cannot count a pre-reference trade.
5. Trade exactly at +336h and immediately after: verify the chosen interval end inclusive/exclusive and minute-resolution rounding.
6. Incomplete, duplicate, zero-trade or out-of-order minute: deterministic INVALID/EXCLUDE, never silent repair.
7. Mutate all trades after decision_at: features and reference price available at decision_at must remain unchanged (PIT metamorphic invariant).
8. Mature negative label: full 336h coverage; a positive early hit does not relax train-data eligibility.
9. Boundary timezone and daylight-saving: UTC only, invariant to host timezone.
10. Preserve a fixed fixture and report exact test command, count, and commit SHA when implemented.

## Acceptance
No G1 freeze until a single consistent contract is selected, corresponding synthetic QA passes, and the actual loader demonstrates the same contract. This document does **not** authorize performance, merge, deployment or LIVE.
