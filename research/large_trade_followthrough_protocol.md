# XRP_LARGE_TRADE_FOLLOWTHROUGH_V1 — frozen protocol (2026-10-25)

Status: **REGISTERED, NOT EVALUATED.** This protocol is committed before performance results.

Distinct hypothesis: unusually large average XRP spot transaction size, accompanied by a positive candle closing near its high, represents informed large-trade participation with short-lived continuation. The observable is Binance quote-asset volume divided by the reported trade count. This is not a price-only relative-return, autocorrelation, calendar, funding/basis, volume-dryup, sweep, or taker-buy-pressure rule.

Fixed 1h XRPUSDT rules: use 168 preceding closed hours, excluding the signal hour, to calculate mean and population standard deviation of log average trade size. Signal if current log average trade size is >=2.0 standard deviations above that causal mean, current close-to-close return is between +0.10% and +1.50%, and candle close location `(close-low)/(high-low)` is >=0.75. Quote volume and trade count must be finite and positive. Enter long at next open. ATR24; stop 1.5 ATR; target 2R; max 8 candles including entry. Stop wins ambiguous bars; gap stop fills at worse open. One non-overlapping position. Risk 0.5% of equity; notional <=20%; no leverage. Fee 9.5 bps/side and adverse slippage 2 bps/side; both doubled in stress.

Actual Binance Vision monthly spot archives Jan 2022–Sep 2026, with URL/SHA256. No missing candles or fabricated fields. 2022 descriptive control; locked OOS years 2023, 2024, 2025 and Jan–Sep 2026, plus a non-independent continuous reconciliation. History is exploratory and parameters will not be changed after evaluation.

All historical gates required: >=150 aggregate OOS trades; positive base net/expectancy and PF>1.15; positive double-cost net/expectancy and PF>1.02; >=3/4 profitable annual folds including 2026; continuous base/stress drawdown <=10%; no month >40% of positive aggregate profit. Historical success remains `TEST NEDOKONCEN` until >=30 future days and >=100 new forward PAPER trades pass base and stress expectancy. No production, LIVE, Render, main or deployed-branch changes.

Next: commit this protocol, implementation and mechanics tests; then run unchanged historical evaluation.
