# BTC_LEAD_LAG_IMPULSE_V1 — frozen protocol (2026-10-25)

Status: **HYPOTHESIS REGISTERED; PERFORMANCE NOT YET EVALUATED.** This file freezes the rules before historical results are calculated.

## Distinct hypothesis

A large positive one-hour BTC spot return that is not yet matched by XRP represents delayed cross-market price transmission. Buy XRP at the next hourly open, then exit on a fixed volatility bracket or after six hours. This is a cross-market lead/lag hypothesis, not relative-strength ranking, serial-autocorrelation regime selection, calendar drift, order-flow pressure, sweep continuation, or a minor parameter change to a rejected strategy.

## Fixed rules

- Markets: Binance spot `BTCUSDT` signal and `XRPUSDT` traded asset, 1h candles.
- A signal uses only the just-closed hour: BTC return >= +1.00%; XRP return in [-0.25%, +0.35%]; BTC minus XRP return >= +0.80%.
- ATR is the arithmetic mean of 24 causal true ranges through the signal candle.
- Enter long XRP at the next candle open with adverse 2 bps slippage.
- Initial stop: 1.5 ATR below the slipped entry. Target: 1.8 times initial risk above entry. Maximum holding time: six candles including the entry candle.
- Stop has priority if stop and target are both touched in one candle. A gap below the stop fills at the worse next open. Exit fills receive adverse 2 bps slippage.
- Fee: 9.5 bps per side. Cost stress doubles both fee and slippage.
- Risk 0.50% of current equity per trade, notional capped at 20% of current equity, no leverage, one XRP position at a time. Signals during an open position are ignored; positions never overlap.
- No missing prices are invented. Both market timestamps must align. A signal requires a complete consecutive 24-hour ATR history. Segment starts flat; segment-end positions are liquidated at the final close with costs.

## Frozen evaluation

Actual Binance Vision monthly archives from January 2022 through September 2026, retaining source URLs and locally computed SHA256 fingerprints. Calendar 2022 is a descriptive control; locked chronological OOS folds are 2023, 2024, 2025, and January–September 2026. The same history has been inspected by earlier hypotheses, so this is exploratory OOS rather than untouched confirmation. There will be no parameter search after viewing results.

Historical screening gates, all required: at least 120 aggregate annual-fold OOS trades; aggregate base PF > 1.15 and positive net P/L/expectancy; aggregate double-cost PF > 1.02 and positive net P/L/expectancy; at least three of four annual OOS folds profitable at base cost; 2026 profitable at base cost; continuous base and stress maximum drawdown <= 10%; no single month contributes more than 40% of positive aggregate OOS profit. Results from annual folds are not independent from the continuous run and will not be double-counted.

Even if every historical gate passes, status remains `TEST NEDOKONCEN`: promotion additionally requires at least 30 future calendar days and 100 new, timestamped, independently accumulated forward PAPER trades with positive base and stressed expectancy. No LIVE, Render, production, or deployed-branch changes are permitted.

Next action: commit this protocol with the isolated implementation and mechanics tests, then run tests and the unchanged runner on real archives.
