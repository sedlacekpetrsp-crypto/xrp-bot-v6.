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
