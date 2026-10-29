# XRP_FINANCIAL_CONDITIONS_EASING_V1 — preregistration (2026-10-29)

Status: HYPOTHESIS REGISTERED; PERFORMANCE HAS NOT BEEN EVALUATED. Historical success alone cannot be PROŠEL without independent forward PAPER evidence.

## Distinct hypothesis

Broad US financial conditions that are already accommodative and continue to ease may improve subsequent risk-bearing capacity for XRP. The observable is the Chicago Fed National Financial Conditions Index (NFCI), a weekly composite of risk, credit and leverage conditions. This is not a crypto price, volume, flow, funding, volatility, calendar, relative-strength, on-ledger, valuation, dollar, VIX or real-yield signal.

A preliminary high-yield-spread source check was not used: the directly returned free FRED BAMLH0A0HYM2 export began only on 2023-10-30 and cannot support the frozen multi-year folds. No earlier values will be fabricated or obtained from a paid source.

## Frozen signal and execution

- Market: XRPUSDT spot daily UTC candles.
- External series: FRED NFCI, weekly, index units.
- Missing NFCI values are not filled. Each valid observation becomes eligible only on the timestamp of the **second subsequent valid weekly observation**, a conservative publication lag.
- At an eligible decision date, require both:
  1. latest lagged NFCI <= -0.25 (accommodative conditions), and
  2. latest lagged NFCI minus its value 8 valid observations earlier <= -0.10 (continued easing).
- Each eligible weekly observation can create at most one signal. Entry is the next XRP daily open; no XRP-return filter.
- ATR14 from closed XRP daily candles; stop 2.0 ATR; target 3R; maximum hold 10 daily bars.
- Long-only spot, one position, no overlap or pyramiding, zero leverage.
- Risk 0.5% of current equity to the initial stop, capped at 20% current-equity notional.
- Base costs: 9.5 bps fee plus 2 bps adverse slippage per side; stress doubles both.
- Gap exits use the adverse open; if stop and target are both touched in one daily candle, stop wins; segment-end liquidation uses an adverse close fill.

No lookback, level, change, exit, sizing or cost parameter will change after observing performance.

## Frozen evaluation

Actual Binance Vision XRPUSDT daily monthly archives January 2020–September 2026 and the direct FRED NFCI CSV. Control is 2020–2021. Locked annual OOS folds are 2022, 2023, 2024, 2025 and January–September 2026. Folds begin flat and use only past warm-up. A continuous 2022–September 2026 run is descriptive and not independent.

Record exact direct URLs and SHA256 before evaluation; reject duplicates/non-monotonic timestamps; report gaps without inventing data; verify external/market alignment and future-prefix invariance. Independently audit signal threshold, publication and next-open lags, costs, gap-stop mechanics, risk/notional size, non-overlap, equity and aggregate arithmetic.

## Frozen promotion gates

All must pass:

1. at least 50 aggregate annual-fold OOS trades;
2. base aggregate net P/L and expectancy > 0, PF > 1.15;
3. double-cost aggregate net P/L and expectancy > 0, PF > 1.02;
4. at least four of five OOS folds profitable at base and stress, including 2026;
5. continuous base/stress max drawdown <= 10%;
6. no single UTC month supplies >25% of positive aggregate OOS trade P/L;
7. all repository tests and an independent audit pass;
8. after every historical gate, at least 30 subsequent calendar days and 50 new timestamped non-overlapping forward PAPER trades with positive base and stressed expectancy.

Without gate 8 the maximum status is historical candidate / TEST NEDOKONČEN, never PROŠEL. No production, main, deployed branch, Render, infrastructure, paused strategy or LIVE change is authorized.

## Next action

Commit source feasibility and SHA256 before performance evaluation; then implement, test, backtest once without tuning, independently audit and record the complete decision.
