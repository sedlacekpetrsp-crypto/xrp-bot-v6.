# XRP_REAL_YIELD_EASING_V1 — preregistration (2026-10-29)

Status: HYPOTHESIS REGISTERED; PERFORMANCE HAS NOT BEEN EVALUATED. A historical pass would still not qualify as PROŠEL without independent forward PAPER evidence.

## Distinct hypothesis

Sustained easing in the US ten-year real yield lowers the external discount rate applied to speculative assets and may support subsequent XRP spot returns. This is an exogenous rates hypothesis. It does not reuse crypto flow, sweep, autocorrelation, weekend, relative-strength, lead/lag, funding, carry, volatility-breakout, VIX-recovery, broad-dollar, on-ledger, holder-growth, valuation, liquidity, or order-book rules.

## Frozen signal and execution

- Market: XRPUSDT spot, daily UTC candles.
- External series: FRED DFII10, 10-Year Treasury Inflation-Indexed Security, Constant Maturity (percent).
- For each valid FRED observation, availability is conservatively assigned to the timestamp of the **second subsequent valid observation**. Missing FRED values are not filled.
- Signal on an XRP daily decision close when the latest available real yield has declined by at least 0.25 percentage point from its value 20 valid FRED observations earlier: current minus lag20 <= -0.25.
- Entry: next XRP daily open. No same-bar entry and no XRP-return condition.
- ATR14 from closed XRP daily candles; initial stop 2.0 ATR below entry; target 3R; maximum holding 10 daily bars.
- Long-only spot, one position maximum, no overlap or pyramiding, zero leverage.
- Risk: 0.5% of current equity to the initial stop, capped at 20% current-equity notional.
- Base costs: 9.5 bps fee plus 2 bps adverse slippage per side. Stress doubles both.
- Gap stop/target fills use the adverse next open; if stop and target are both touched within one candle, stop wins. Segment-end liquidation uses an adverse close fill.

No threshold, lookback, exit, sizing, or cost parameter will be changed after inspecting results.

## Frozen evaluation

Actual Binance Vision XRPUSDT daily monthly archives, January 2020 through September 2026, plus the directly downloaded FRED CSV. The control period is 2020–2021. Locked chronological OOS folds are calendar 2022, 2023, 2024, 2025, and January–September 2026. Each fold begins flat with warm-up restricted to preceding observations. A separate continuous 2022–September 2026 run is descriptive and cannot be added to fold trades as independent evidence.

Before evaluation record every direct URL and SHA256; reject duplicate or non-monotonic timestamps; report gaps without inventing prices; verify market/external alignment and prefix invariance against future-data leakage. Independently audit signals, next-open timing, costs, gap stops, sizing, non-overlap, equity reconciliation, and summary arithmetic.

## Frozen promotion gates

All must pass at base and double costs where applicable:

1. at least 75 aggregate annual-fold OOS trades;
2. aggregate OOS net P/L and expectancy > 0, PF > 1.15;
3. stress aggregate OOS net P/L and expectancy > 0, PF > 1.02;
4. at least four of five OOS folds profitable at base costs, including 2026;
5. continuous OOS max drawdown <= 10% at base and stress;
6. no single UTC month supplies > 25% of positive aggregate OOS trade P/L;
7. complete code tests and independent audit;
8. after all historical gates, at least 30 subsequent calendar days and 75 new, timestamped, non-overlapping forward PAPER trades with positive base and stressed expectancy.

Without gate 8 the strongest permissible status is historical candidate / TEST NEDOKONČEN, never PROŠEL. No production, Render, infrastructure, paused strategy, or LIVE change is authorized.

## Next action

Commit source feasibility and provenance before performance evaluation, then implement, test, backtest without tuning, independently audit, and record the complete decision.
