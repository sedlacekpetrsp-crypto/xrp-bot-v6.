# XRP_SPOT_PERP_CARRY_V1 — frozen protocol

Frozen: 2026-10-27, before performance evaluation. Historical results were not inspected while selecting these rules. This is exploratory PAPER-only research and is not evidence of profitability.

## Distinct hypothesis

When XRP perpetual futures already trade above spot and the latest published funding rate is materially positive, an equal-notional long-spot/short-perpetual position can earn the subsequent funding cashflows while reducing outright XRP direction. This tests exchange carry capture, not the previously rejected directional funding reversal, continuous-premium recovery, relative strength, volume attention, order-book, autocorrelation, breadth, or momentum mechanisms. It never sends orders and never touches a production bot.

## Frozen data and chronology

- Market: Binance XRPUSDT spot 1h klines, USD-M perpetual mark-price 1h klines, and published USD-M funding-rate records.
- Archives: actual Binance Vision monthly files, January 2022 through September 2026. Preserve exact URLs, byte counts, and locally calculated SHA256 fingerprints.
- Align spot and mark bars by exact open timestamp. Never synthesize a missing price or funding record. A signal, open position, or 168-hour holding path may not cross a missing aligned hour.
- Normalize publisher funding timestamps to the nearest hour only when the absolute recorded offset is at most one second; retain and report every adjustment. This is the already documented ingestion convention, not performance tuning.
- A signal uses only the latest funding event published at or before a completed hourly bar and that bar's closes. Entry is at the next hourly open. Annual folds start flat and use earlier data only for state; no position crosses a fold boundary.
- 2022 is a control period. Locked chronological OOS folds are calendar years 2023, 2024, 2025, and 2026 through September. Also report one continuous 2023–September 2026 path without treating it as independent evidence.

## Frozen trading rules

- Signal after a completed aligned hourly bar when the latest funding rate is at least +0.030% and mark/spot close premium is at least +0.10%.
- Open next hour: long spot and short perpetual at equal 10% equity notionals (20% gross, zero leverage, no overlapping position). Quantities remain fixed until pair exit.
- Base adverse entry/exit slippage: 0.02% on each leg each side. Fees: 0.095% spot and 0.05% perpetual on each side. Stress doubles every fee and slippage rate; funding cashflows are not doubled.
- At each funding timestamp strictly after entry and before exit, the short receives `perpetual quantity * mark close * published funding rate`; a negative rate is therefore a payment. No unobserved funding is inferred.
- Exit both legs at the next open after the first completed bar whose close premium is non-positive, or at the open after 168 completed hours, whichever comes first.
- Pair stop: entry premium +1.50 percentage points. If the next bar's opening premium is already at/above it, exit at that worse open (gap stop). Otherwise, if `mark high / spot low - 1` reaches the stop during a bar, use the conservative adverse fills of that bar's mark high for the short and spot low for the long. Stop wins over any discretionary/time exit in an ambiguous bar.
- Before any normal exit, require the current bar and next opening bar to be consecutive. If a data gap would be crossed, liquidate at the last observed closes with adverse exit slippage and record `DATA_GAP`; do not invent the missing open.
- Equity is marked and debited/credited after every closed pair. Position sizing uses only equity known before entry. Full ledgers must reconcile gross leg P/L, funding cashflows, fees, slippage, and net P/L.

## Frozen acceptance gates

Historical promotion requires all of the following, without parameter adjustment:

1. At least 60 aggregate annual-fold OOS trades.
2. Aggregate OOS net P/L and expectancy positive, with PF > 1.15 at base costs.
3. Aggregate OOS net P/L and expectancy positive, with PF > 1.02 at doubled costs.
4. At least three of four OOS annual folds positive at base costs, including 2026; at least three positive under stress.
5. Continuous OOS maximum drawdown no more than 10% at base and stress costs.
6. No one annual fold supplies more than 40% of the sum of positive annual profits.
7. Code tests cover next-open chronology, funding inclusion boundaries, no overlaps, cost stress, conservative intrabar stop, gap stop, missing-data exit, position caps, and prefix invariance. An independent ledger audit must pass.

Even if every historical gate passes, status remains `TEST NEDOKONCEN`: acceptance additionally requires at least 30 calendar days and 100 new, timestamped, independent forward PAPER decisions under these frozen rules, with positive stressed expectancy and the same risk controls. Historical success or code-test success alone can never produce `PROSEL`.

## Next action

Implement the isolated simulator and independent audit, run all repository tests, download and validate the frozen real-data set, execute control/OOS/stress paths once, and commit complete provenance, results, compressed ledgers, decision, and the next concrete research step. Do not alter main, `v8-fly-layer-test`, Render, production configuration, or LIVE trading.
