# XRP_VOLATILITY_COMPRESSION_BREAKOUT_V1 — frozen protocol

Frozen: 2026-10-27, before performance evaluation. Historical results were not inspected while selecting these rules. PAPER-only research; no claim of profitability.

## Distinct hypothesis

After an unusually quiet 24-hour XRP volatility state, a close above the preceding 72-hour range may begin a multi-day volatility expansion with positive directional follow-through. This is a transition from low realized range to expansion. It is not the rejected autocorrelation regime switch, liquidity sweep, flow pressure, relative strength, volume attention, funding/premium, crowding, breadth, illiquidity, or carry mechanism. It uses no volume or derivatives field.

## Frozen data and chronology

- XRPUSDT Binance spot 1-hour klines, January 2022 through September 2026, from actual monthly Binance Vision archives.
- Preserve every archive URL, downloaded byte count, row count, and locally calculated SHA256. The hash identifies downloaded bytes and is not a publisher signature.
- Never fill or interpolate a missing bar. ATR, percentile history, breakout history, and an open trade must consist only of consecutive timestamps. If a position reaches a missing next hour, liquidate at the last observed close with adverse exit slippage and label `DATA_GAP`.
- 2022 is the control period. Locked chronological OOS folds are 2023, 2024, 2025, and January–September 2026. Report a continuous 2023–September 2026 path, but do not count it as independent evidence.
- Each fold starts flat. Earlier bars may warm causal indicators, but no position or equity crosses a fold boundary.

## Frozen signal and execution

1. Compute Wilder-independent simple ATR(24) from 24 completed true ranges. Normalize by that bar's close.
2. On bar `i-1`, compression exists when normalized ATR is at or below the 20th percentile of the preceding 720 normalized ATR observations, excluding `i-1`. All 744 required hours must be consecutive.
3. Signal on completed bar `i` only when its close is strictly above the maximum high of bars `i-72` through `i-1`. The compression bar is therefore fixed before the breakout bar and the breakout cannot change its threshold.
4. Enter long XRP spot at bar `i+1` open with adverse slippage. No shorting or leverage.
5. Stop is entry minus 2.0 times ATR known at `i-1`; target is entry plus 3.0 initial risks; time exit is the close of the 72nd held hourly bar.
6. Risk 0.50% of current fold equity to the stop, capped at 20% notional. One position at a time; signals during a position are ignored.
7. Base fee is 0.095% per side and adverse slippage is 0.02% per side. Stress doubles both. Gap stop fills at the worse open; if stop and target are both inside one OHLC bar, stop wins. Position size and brackets are not changed after entry.

## Frozen acceptance gates

All must pass without parameter adjustment:

1. At least 100 aggregate annual-fold OOS trades.
2. Aggregate base OOS net P/L and expectancy positive, PF > 1.15.
3. Aggregate doubled-cost OOS net P/L and expectancy positive, PF > 1.02.
4. At least three of four annual OOS folds positive at base costs, including 2026; at least three positive under stress.
5. Continuous OOS drawdown no more than 10% at base and stress costs.
6. No single calendar month contributes more than 40% of the sum of positive OOS monthly profits.
7. Repository tests cover causal signal timing, prefix invariance, next-open entry, missing-bar suppression/exit, sizing, costs, doubled-cost deterioration, gap stop, intrabar ambiguity, non-overlap, and fold boundaries. An independent ledger audit must pass.

Even if all historical gates pass, status remains `TEST NEDOKONCEN` until at least 30 calendar days and 100 new timestamped independent forward PAPER decisions under the frozen rules have positive stressed expectancy and pass the same controls. Historical success and code-test success alone never justify `PROSEL`.

## Next action

Commit this protocol before evaluation; then implement and unit-test the isolated simulator, download and validate the real archives once, run the fixed control/OOS/stress paths, independently audit the ledger, and commit complete evidence and decision. Do not modify main, `v8-fly-layer-test`, Render, production configuration, paused strategies, or LIVE trading.
