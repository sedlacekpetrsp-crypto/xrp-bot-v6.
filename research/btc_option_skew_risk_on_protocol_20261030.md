# BTC_OPTION_SKEW_RISK_ON_XRP_V1 — frozen protocol (2026-10-30)

Status: **PREREGISTERED; PERFORMANCE NOT YET EVALUATED.** Offline research only.

## Distinct hypothesis

BTC option buyers sometimes pay more implied volatility for upside calls than downside puts. A positive near-25-delta risk reversal is hypothesized to identify asymmetric crypto upside demand that carries into XRP. This tests the *shape* of option-implied tail pricing, not the absolute DVOL level or DVOL-minus-realized variance premium already rejected, and it does not use price direction, relative strength, volume/flow, funding, OI, macro or on-chain activity.

## Fixed causal metric

Use only public historical BTC option trade records from Deribit's official History API. For every Friday, retrieve all option trades from 12:00:00.000 through 12:59:59.999 UTC. Bisect any API interval reporting `has_more=true` until every used response is complete; deduplicate by trade ID. Retain every exact URL, byte count and local SHA256. Do not fill an absent trade or quote.

Parse plain BTC option instruments, reported trade IV and index price. Estimate Black-Scholes delta at the trade timestamp with reported IV, strike, expiry and index, zero rates and no dividend. Keep 14–60 calendar-day maturity and absolute delta 0.15–0.35. Require at least five distinct call trades, five put trades and aggregate reported amount >=1 on each side. The weekly skew is unweighted median call IV minus unweighted median put IV in percentage points. This is a trade-print proxy, not a synchronized executable quote surface. A strictly positive skew signals risk-on. No magnitude threshold or post-hoc interpolation is allowed.

The observation closes Friday 13:00 UTC. Enter XRPUSDT spot only at the next Monday 00:00 UTC open. A missing/insufficient week creates no signal, not a synthetic value.

## Fixed execution

Long XRP spot, zero leverage, one position. ATR14 uses preceding closed daily candles. Stop two ATR below the adverse entry fill, target 3R, maximum seven daily candles including entry. Stop wins same-candle ambiguity; a gap through stop fills at the worse open, while a gap above target remains capped at target. Fees are 9.5 bps and adverse slippage 2 bps per side; stress doubles both. Risk 0.5% of current equity at stop and cap entry notional at 20%. Skip overlapping signals. A price gap exits at the last actual pre-gap close. No borrowing or funding.

## Locked evaluation and gates

Use direct Binance daily XRP spot prices and Deribit option trades from January 2021 through September 2026. Calendar 2021 is control; annual OOS folds are 2022–2026 through September, plus a separate continuous diagnostic. Preserve actual-source hashes, coverage/rejection reasons, ledgers and an independent audit. No parameter optimization follows results.

All historical gates are required: >=100 aggregate annual-fold OOS trades; positive base net and expectancy with PF>1.20; positive double-cost net and expectancy with PF>1.05; >=4/5 years positive at both costs including 2026; continuous base/stress drawdown <=10%; no year >50% of positive annual profit; and independent audit of source hashes, recursive completeness, deduplication, option parsing, delta/maturity filters, medians, lag, OHLC, fills, costs, sizing, gap-stop, non-overlap, equity and reports.

Even a complete historical pass remains `TEST NEDOKONCEN` until >=365 future calendar days and >=50 newly timestamped forward PAPER trades show positive base and stressed expectancy under unchanged rules. Tests or historical profit never mean `PROSEL`. Failed completed gates mean `NEPROSEL`. Do not change the Friday hour, maturity/delta bands, minimum observations or skew sign on these dates.

Next action: commit this protocol, code, downloader, audit and mechanics tests remotely before evaluating returns; then run the unchanged multi-year validation. Do not touch production, Render, LIVE, main, paused strategies or `v8-fly-layer-test`.
