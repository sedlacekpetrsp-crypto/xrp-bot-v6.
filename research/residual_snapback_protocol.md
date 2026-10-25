# XRP_RESIDUAL_SNAPBACK_V1 — frozen protocol (2026-10-25)

Status: **REGISTERED; PERFORMANCE NOT YET EVALUATED.** Rules and gates are frozen before calculation.

Hypothesis: an extreme negative one-hour XRP return unexplained by a causal BTC/ETH market factor is temporary idiosyncratic dislocation and mean-reverts. This differs from rejected relative-strength momentum, BTC lead/lag, pairs momentum, flow, sweep, autocorrelation and calendar hypotheses.

Fixed rules: Binance spot XRPUSDT/BTCUSDT/ETHUSDT 1h. At every closed hour form the equal-weight BTC/ETH log-return factor. Using the preceding 168 returns only (excluding the current return), fit zero-intercept XRP beta `sum(x*f)/sum(f*f)` and calculate historical residual standard deviation. Signal when current residual is <= -2.5 standard deviations while the current factor return is >= -0.5%. Enter XRP long at the next open. ATR24; stop 1.75 ATR, target 1.5R, maximum 12 candles including entry. Stop wins ambiguous candles; a gap below stop fills at the worse open. One position; signals while open ignored. No leverage. Risk 0.5% current equity; notional <=20%. Fee 9.5 bps and adverse slippage 2 bps each side; stress doubles both.

No price imputation. Markets must align; a signal requires an uninterrupted 168-hour history. Actual Binance Vision archives Jan 2022–Sep 2026 with URLs and local SHA256. 2022 is descriptive control; chronological OOS folds: 2023, 2024, 2025, Jan–Sep 2026, plus a non-independent continuous reconciliation run. History is exploratory because prior strategies inspected it. No parameter changes after results.

All historical gates required: >=150 aggregate annual-fold OOS trades; base net and expectancy positive, PF>1.15; doubled-cost net and expectancy positive, PF>1.02; >=3/4 profitable annual folds including 2026; continuous base/stress drawdown <=10%; no single month >40% of positive aggregate profit. Historical passage still means `TEST NEDOKONCEN` until >=30 new calendar days and >=100 independently accumulated forward PAPER trades have positive base and stressed expectancy. No LIVE, production, Render or deployed-branch changes.

Next: commit protocol, isolated implementation and mechanics tests; then run unchanged code on real data.
