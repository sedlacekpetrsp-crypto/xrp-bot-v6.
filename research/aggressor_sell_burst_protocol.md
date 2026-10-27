# XRP_AGGRESSOR_SELL_BURST_REVERSAL_V1 — frozen protocol

Frozen: 2026-10-27 before performance evaluation. PAPER-only research; no profitability claim.

## Distinct hypothesis

A sharp one-minute decline dominated by a long uninterrupted sequence of seller-initiated aggregate trades may represent short-lived execution exhaustion, followed by a mechanical rebound. The signal uses the order and aggressor side of actual tick-level Binance spot `aggTrades`, resets runs at each UTC minute, and trades reversal. This is not the rejected FLOW_PRESSURE_V1, which used three 15-minute aggregate taker-buy volume/volume/reference-price conditions and traded continuation. It is also independent of the rejected candle sweep, volatility, relative-strength, attention, funding, premium, crowding, breadth, order-book-depth, or carry rules.

## Frozen data and derivation

- Actual Binance Vision monthly XRPUSDT spot aggregate-trade archives, January 2022 through September 2026. Preserve source URL, downloaded byte count, record count, first/last aggregate-trade ID and time, and local SHA256.
- Row fields are aggregate-trade ID, price, quantity, first/last underlying trade IDs, transaction timestamp, buyer-maker flag, and best-match flag. `buyer_maker=True` is seller-initiated; `False` is buyer-initiated.
- Construct UTC one-minute bars directly from all aggregate trades: first/maximum/minimum/last price, aggregate-event count, seller-event count, and maximum consecutive seller-initiated event run. A run resets at every minute boundary. Event counts are aggregate-trade events, not inferred individual fill counts.
- Validate strictly increasing aggregate-trade IDs and nondecreasing timestamps. Record ID discontinuities. Mark both adjacent minutes invalid around any ID discontinuity; invalid minutes cannot signal or be held through. Never synthesize a trade or price. Missing calendar minutes remain missing.
- 2022 is control. Locked OOS folds are 2023, 2024, 2025, and January–September 2026. Report a continuous 2023–September 2026 path without counting it as independent evidence. Each fold starts flat; no position crosses a fold boundary.

## Frozen signal and execution

After a complete closed UTC minute, signal long only when all are true:

1. maximum consecutive seller-initiated aggregate-trade run is at least 25;
2. seller-initiated events are at least 75% of all aggregate-trade events in that minute;
3. minute close is at least 0.20% below its open.

Enter at the next exact minute's first aggregate-trade price with 0.02% adverse slippage. Stop is 0.60% below filled entry; target is 1.20% above filled entry; maximum hold is 30 complete minutes. Fee is 0.095% per side. Stress doubles fee and slippage. Size risks 0.50% of current fold equity to the stop, capped at 20% notional, zero leverage, one position at a time. Signals during an open position are ignored.

On every derived minute, a gap-open at/below stop exits at that worse open; otherwise stop wins over target if both appear in the same minute. If an invalid/missing next minute or aggregate-ID discontinuity interrupts a position, exit at the last trustworthy close with adverse exit slippage and label `DATA_GAP`. At a fold end, liquidate at the last trustworthy close. No borrow, short, or funding model is needed because execution is spot long only.

## Frozen acceptance gates

All must pass without parameter changes:

1. At least 250 aggregate annual-fold OOS trades.
2. Aggregate base OOS net P/L and expectancy positive, PF > 1.15.
3. Aggregate doubled-cost OOS net P/L and expectancy positive, PF > 1.02.
4. At least three of four annual OOS folds positive at base costs, including 2026; at least three positive under stress.
5. Continuous OOS drawdown <=10% at base and stress costs.
6. No single calendar month contributes more than 25% of the sum of positive OOS monthly profit.
7. Tests cover tick aggregation/run reset, side classification, causal next-minute entry, prefix invariance, ID/time gaps, non-overlap, costs, sizing, stress, gap-stop, ambiguous stop priority, and fold boundaries. An independent ledger audit must pass.

Even a complete historical pass remains `TEST NEDOKONCEN` until at least 30 calendar days and 100 new timestamped forward PAPER decisions under the frozen rules have positive stressed expectancy and pass the same controls. Historical or code-test success alone never produces `PROSEL`.

## Next action

Commit these rules before evaluation; implement a streaming archive parser and isolated simulator, run repository tests, process the real archives once, audit full ledgers independently, and commit provenance, results, limitations, decision, and next step. Do not modify main, `v8-fly-layer-test`, Render, production configuration, paused strategies, infrastructure, or LIVE trading.
