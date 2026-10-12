# PAPER bot technical audit — 2026-10-11

Source: v8-fly-layer-test, baseline 47e2acc2785268463118f87a85e7b79645d746f5.

TV already requires closed 1m momentum and aligned 5m/15m trend. These filters were not duplicated or relaxed. STALE TRADE previously counted repeated 15-second polls of the same candle as two confirmations. It now requires two increasing, distinct closed 1m candle timestamps, persists its count/timestamp and ignores missing/out-of-order timestamps. Existing positions without the timestamp discard the old ambiguous confirmation count. Entry risk, SL/TP and other exits are unchanged.

Whale keeps a bounded 500-observation journal in the existing state JSON, including candidate keys, entry/stop/target, rejection reasons and observed scan prices. The shared dashboard's normal status response omits this journal; /whale/signal-journal exposes it separately. This is sampled diagnostic evidence, not a counterfactual backtest: intrabar paths, unobserved quotes and realized hypothetical profit cannot be inferred. Journal samples begin with this deployment; historical rejection records were not previously persisted. No filters were loosened.

FLY /fly/accounting-audit reads all persisted trades rather than the in-memory truncated history. Read-only audit on 11 October confirmed 287 records, net P/L -839.9706208936245, stored PAPER balance 9327.277655852935. With initial capital 10000, the ledger balance is 9160.029379106376 and the difference is +167.248276746559. Three opening fingerprints each have two closes with differing P/L. These cannot be resolved by deleting identical rows, and they do not alone explain the balance discrepancy. No history or balance was rewritten. FLY, FAST and Lead-Lag remain paused.

Validation: 20 focused tests pass (test_paper_audit_regressions, test_exit_regressions, test_whale_execution_freshness, test_bestof_portfolio), Python compilation and git diff --check pass. FLY double close, restart replay, persisted duplicate and failed transaction paths are checked with isolated functions/database mocks. This does not prove real PostgreSQL concurrency or crash recovery.

Six failures in test_whale_fib_vwap and test_whale_signals were reproduced on an unchanged baseline archive; these suites still expect older pullback/Telegram scanner behavior. They are not reported as passing. No profitability backtest was performed and no claim of improved returns is made. A new entry filter or replacement strategy requires cost-inclusive evaluation on an unused period before deployment.

## Follow-up: identity races and reconciliation sensitivity

FLY's exit manager now verifies position object identity after awaiting both live price and indicators. If another task closed/replaced the position during the wait, the stale task returns without writing stops or closing the replacement. Invalid live prices are rejected before mutation. This is an additional technical fix, not evidence that it caused every historical duplicate or the full balance discrepancy.

Read-only SQL confirmed every recorded P/L equals gross P/L minus recorded fees. The three later duplicate closes total -33.328148182659355 USDC. Counting only the earliest close for each fingerprint would yield net P/L -806.6424727109649 and balance 9193.357527289035, still 133.920128563900 below the saved balance. The first-close-only calculation is an explicit sensitivity assumption, not a repaired ledger. Two October 2 duplicate pairs also used different fee rates (0.05% and 0.095% per side); exact writer provenance and the remainder cannot be recovered from available state alone. No balance adjustments or exclusions were applied.

Whale journal persistence was confirmed directly in blue_whale_state (27 observations at 07:29 UTC, then 45). Initial candidates included two hour-trend vetoes and one stop-distance veto. This sample is insufficient for changing filters. Multiple observations can refer to the same candidate and are not independent trades.

The focused suite now has 24 passing tests, including replacement/closure during a price await, replacement during an indicator await, and invalid-price nonmutation. PostgreSQL transaction tests still use mocks.

## Hidden scanner worker found and disabled

Candle Scanner branch v8-candle-scanner has an integrated FLY worker using the same v8fixed_state/v8fixed_trades tables and an older multi-position engine. Its code accounts for MARKET STOP records and uses fixed fee 0.0005 versus 0.00095 in the current shared engine. On 11 October the scanner /health reported enabled=true and running=true while the shared dashboard FLY was paused. This establishes a second enabled writer and a concrete conflict mechanism, but does not reconstruct all historic cash mutations.

The diagnostic HTTP request woke the free service; the legacy worker opened ETHUSDC, SOLUSDC and XRPUSDC PAPER shorts at 07:39 UTC. No exchange orders exist. FLY_INTEGRATED_ENABLED was set false on the scanner service using a merge update; its replacement deploy is live. These three residual simulated positions must be settled rather than abandoned. The recovery is scoped to their exact opening fingerprints, uses observed fresh exit quotes, the deployed legacy engine's fixed fee/slippage constants (0.0005/0.0002), checks a state lease under row lock, and writes all trade records and the balance delta in one transaction with settlement claims. Original records and the full recovered position snapshots are retained. Partial positions, unexpected openings, stale state and duplicate claims fail closed. Shared FLY cycles remain blocked while recovery runs. No historical account offset is adjusted.

Thirty focused tests pass, including one-time settlement, repeat startup, rollback, changed-state refusal, unexpected opening refusal and recovery cost arithmetic. Transaction tests use mocks; deployment/database verification is separately required.

## User-authorized correction and loss review — 12 October

The user explicitly requested repair, then changes to reduce losses. A one-time canonical PAPER reconciliation now retains all 290 raw trade rows, marks later close ids 250/290/314 as excluded, and consistently uses the earliest recorded close for each identical opening. Canonical count is 287, net P/L -821.7950517690388 USDC, and balance 9178.20494823096. The correction from saved balance 9312.12507679486 is -133.92012856390 and is recorded separately as an accounting adjustment, not a new losing trade. The cause of the historical overwritten cash state is not retroactively reconstructed. Exclusions, prior/new balance, policy and provenance limitation are retained in separate audit tables. The startup migration requires the exact reviewed ledger, no open positions and paused FLY, and is idempotent. Raw history is never deleted.

The TV validation compares nine preregistered ADX/ATR combinations, all negative. TV new entries are paused with exit management retained and a visible dashboard label. NEWS_LONG remains independent, including its RSS refresh and account. No risk is increased and no profitable replacement is claimed. See research/tv_validation_20261012/README.md and protocol/results.

Validation: 46 focused tests pass including transaction rollback/idempotency, changed-ledger/open-position refusal, reviewed history retention, canonical audit, TV pause with retained exits, future-bar masking and independent NEWS behavior. Database transaction tests use mocks; actual deployment and database invariants require verification.
