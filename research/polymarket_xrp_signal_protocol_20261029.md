# POLYMARKET_XRP_SIGNAL_V1 — preregistration (2026-10-29)

Status: HYPOTHESIS REGISTERED; PERFORMANCE HAS NOT BEEN EVALUATED. The source must pass the frozen history/quality gates before any historical backtest.

## Distinct hypothesis

The traded probability in Polymarket's five-minute XRP Up/Down market may incorporate short-horizon information before Binance XRPUSDT spot. This is prediction-market microstructure, not a price-only, flow, funding, volatility, calendar, relative-strength, on-chain, valuation or macro rule.

## Frozen signal and execution

For every official Polymarket event in series slug `xrp-up-or-down-5m`:

- Market window is the event's exact five-minute `startTime` through `endDate`; outcome must be Up/Down and resolution source Chainlink XRP/USD.
- Decision time is start + 120 seconds.
- Use only public Data API trades timestamped from market start through decision time. Identify the Up token from Gamma `outcomes` and `clobTokenIds`.
- Compute Up probability as the volume-weighted mean price of Up-token trades during the last 60 seconds ending at decision time. SELL trades are still trades in the Up token; price is the Up share price.
- Require probability >= 0.65, at least $250 matched Up-token notional in that 60-second window, and at least 10 trades. No later trade or resolution price may enter the signal.
- Long-only Binance XRPUSDT spot. Enter at the next complete Binance one-minute candle open after decision time and exit at the open at/after the Polymarket end time. At most one position; skip overlap.
- Position notional is 10% current equity, no leverage. Base cost is 9.5 bps fee plus 2 bps adverse slippage per side; stress doubles both. There is no intrawindow stop because one-minute OHLC cannot reconstruct sub-minute ordering; exposure is capped by fixed small notional and the three-minute maximum holding interval.
- Exact market alignment must be within one second and no missing Binance price may be synthesized.

No probability, volume, trade-count, decision-time, sizing or cost threshold will be changed after performance inspection.

## Frozen source and evaluation gates

Before backtesting, require:

1. official Gamma metadata and public trade records for at least 95% of all expected consecutive five-minute XRP markets in each included day;
2. at least two complete calendar years of source history, because the parent research mandate requires multi-year testing;
3. at least 1,000 eligible markets after causal liquidity filters;
4. immutable direct URLs plus SHA256 of every fetched response, explicit pagination and duplicate detection;
5. a chronological split with the last six complete months locked OOS and never used for parameter selection;
6. code tests for token mapping, causality cutoff, VWAP, next-open timing, costs, non-overlap, missing-data rejection and prefix invariance.

Historical promotion would then require >=300 OOS trades, positive net and expectancy, PF >1.15; doubled-cost positive net/expectancy and PF >1.02; at least four of six OOS months profitable at both costs; max drawdown <=10%; no month >25% of positive profit. Even after all historical gates, PROŠEL additionally requires 30 subsequent days and 300 new timestamped forward PAPER trades with positive stressed expectancy.

If official history cannot meet gates 1–3, the correct status is TEST NEDOKONČEN, not NEPROŠEL: no performance conclusion is permitted. No proxy probability from Binance price, resolved outcome, webpage odds or fabricated missing records is allowed. No production, Render, infrastructure, paused strategy or LIVE change is authorized.

## Next action

Commit a reproducible official-source coverage audit, exact payload hashes, tests and limitations. Run performance only if all frozen source gates pass.
