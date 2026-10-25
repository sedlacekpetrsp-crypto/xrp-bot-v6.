# XRP_RESIDUAL_SNAPBACK_V1 — frozen protocol (2026-10-25)

Status: **REGISTERED; PERFORMANCE NOT YET EVALUATED.** Rules and gates are frozen before calculation.

Hypothesis: an extreme negative one-hour XRP return unexplained by a causal BTC/ETH market factor is temporary idiosyncratic dislocation and mean-reverts. This differs from rejected relative-strength momentum, BTC lead/lag, pairs momentum, flow, sweep, autocorrelation and calendar hypotheses.

Fixed rules: Binance spot XRPUSDT/BTCUSDT/ETHUSDT 1h. At every closed hour form the equal-weight BTC/ETH log-return factor. Using the preceding 168 returns only (excluding the current return), fit zero-intercept XRP beta `sum(x*f)/sum(f*f)` and calculate historical residual standard deviation. Signal when current residual is <= -2.5 standard deviations while the current factor return is >= -0.5%. Enter XRP long at the next open. ATR24; stop 1.75 ATR, target 1.5R, maximum 12 candles including entry. Stop wins ambiguous candles; a gap below stop fills at the worse open. One position; signals while open ignored. No leverage. Risk 0.5% current equity; notional <=20%. Fee 9.5 bps and adverse slippage 2 bps each side; stress doubles both.

No price imputation. Markets must align; a signal requires an uninterrupted 168-hour history. Actual Binance Vision archives Jan 2022–Sep 2026 with URLs and local SHA256. 2022 is descriptive control; chronological OOS folds: 2023, 2024, 2025, Jan–Sep 2026, plus a non-independent continuous reconciliation run. History is exploratory because prior strategies inspected it. No parameter changes after results.

All historical gates required: >=150 aggregate annual-fold OOS trades; base net and expectancy positive, PF>1.15; doubled-cost net and expectancy positive, PF>1.02; >=3/4 profitable annual folds including 2026; continuous base/stress drawdown <=10%; no single month >40% of positive aggregate profit. Historical passage still means `TEST NEDOKONCEN` until >=30 new calendar days and >=100 independently accumulated forward PAPER trades have positive base and stressed expectancy. No LIVE, production, Render or deployed-branch changes.

Next: commit protocol, isolated implementation and mechanics tests; then run unchanged code on real data.

## Completed validation (2026-10-25)

Decision: **NEPROŠEL**. The frozen rules were committed as `88f4039600997677b804db077e9d3a091ef170aa` before performance evaluation. All 35 repository research tests passed, including six new causality, gap, alignment, execution, cost, sizing and non-trading tests. The existing independent ledger audit also passed chronology, next-open timing, non-overlap, sizing, cost arithmetic, equity and report reconciliation.

The test validated 171 real Binance Vision monthly archives, 41,615 aligned hourly candles per market, January 2022–September 2026. The common 2023-03-24 13:00 UTC missing candle was not fabricated; signals require uninterrupted history. Source URLs and locally computed SHA256 fingerprints are in `results.json`.

Annual-fold OOS: 231 trades, -$2,029.15 net, PF 0.563, expectancy -$8.78/trade. Doubled costs: -$3,007.28, PF 0.424, expectancy -$13.02. Every OOS year lost at base costs. Continuous OOS returned -18.98% with 20.16% conservative drawdown; stress returned -27.05% with 27.74% drawdown. Only the sample-size gate passed; every profitability, stability, final-period, drawdown and concentration gate failed. The 2022 control also lost (-6.10%, PF 0.576). No forward PAPER stage is justified.

Full provenance/metrics: `research/residual_snapback_validation_20261025/results.json`; ledger: `trades.json.gz`; independent audit: `audit.json`. Do not tune this residual threshold, holding period or brackets on these observed folds. Next research must use a structurally different mechanism. No production, LIVE, Render or deployed branch was changed.
