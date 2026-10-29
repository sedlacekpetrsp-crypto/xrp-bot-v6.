# XRP_EXTREME_FEAR_CONTRARIAN_V1 — preregistration (2026-10-29)

Status: HYPOTHESIS REGISTERED; PERFORMANCE HAS NOT BEEN EVALUATED. Historical success alone cannot be PROŠEL without independent forward PAPER evidence.

## Distinct hypothesis

Broad crypto-market extreme fear can create temporary forced-risk reduction and an excessive discount in XRP; buying only under a deeply fearful external sentiment reading may earn a subsequent mean-reversion premium. The observable is Alternative.me's published Crypto Fear & Greed Index, not XRP price/volume/order flow, funding, volatility, calendar, relative strength, on-chain activity, valuation, macro rates, VIX or Polymarket odds.

## Frozen signal and execution

- Market: XRPUSDT spot daily UTC candles.
- External series: Alternative.me Crypto Fear & Greed Index, integer 0–100.
- At XRP decision close on date D, only the index stamped D-1 or earlier is eligible (full calendar-day publication lag). Exact daily dates only; no fill/interpolation.
- Signal when the latest eligible index value is <=20. Classification text is descriptive and not used.
- Entry at the next XRP daily open after the decision close. No XRP return or volume confirmation.
- ATR14 from closed XRP daily candles; stop 2.0 ATR; target 3R; maximum hold 10 daily bars.
- Long-only spot, one position, no overlap/pyramiding, zero leverage.
- Risk 0.5% current equity to initial stop, capped at 20% current-equity notional.
- Base costs: 9.5 bps fee plus 2 bps adverse slippage per side; stress doubles both.
- Gap stop/target uses the adverse open; if stop and target touch in one daily candle, stop wins; segment-end liquidation uses adverse close fill.

No sentiment threshold, lag, exit, sizing or cost parameter will change after performance inspection.

## Frozen evaluation

Direct Alternative.me API payload and actual Binance Vision XRPUSDT daily monthly archives. Use 2020–2021 as control; locked annual OOS folds 2022, 2023, 2024, 2025 and January–September 2026. Folds start flat with past-only warm-up. A separate continuous 2022–September 2026 path is descriptive and cannot be added to annual trades.

Retain every direct URL, byte count and SHA256; reject duplicate/non-monotonic timestamps; require exact daily alignment; report gaps without inventing data; test prefix invariance. Independently audit full-day metric lag, next-open entry, <=20 threshold, fees/slippage, gap stops, risk/notional size, non-overlap, equity and aggregate arithmetic.

## Frozen promotion gates

All must pass:

1. at least 75 aggregate annual-fold OOS trades;
2. base aggregate net P/L and expectancy >0, PF >1.15;
3. double-cost aggregate net P/L and expectancy >0, PF >1.02;
4. at least four of five OOS folds profitable at base and stress, including 2026;
5. continuous base/stress max drawdown <=10%;
6. no single UTC month supplies >25% of positive aggregate OOS trade P/L;
7. all tests and independent audit pass;
8. after all historical gates, at least 30 subsequent calendar days and 75 new timestamped non-overlapping forward PAPER trades with positive base and stressed expectancy.

Without gate 8 the strongest permitted status is historical candidate / TEST NEDOKONČEN, never PROŠEL. No production, main, deployed branch, Render, infrastructure, paused strategy or LIVE change is authorized.

## Next action

Commit exact source feasibility and SHA256 before evaluation, then implement, test, run the single frozen backtest without tuning, independently audit and record the decision.
