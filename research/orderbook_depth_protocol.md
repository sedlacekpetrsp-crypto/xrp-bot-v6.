# XRP_ORDERBOOK_DEPTH_IMBALANCE_V1 — frozen protocol

Status: preregistered before historical performance evaluation on 2026-10-26. No profitability claim.

## Distinct hypothesis

An unusually bid-heavy perpetual-futures order book within 1% of mid price represents passive support that predicts a short-horizon XRP spot rise. This uses published resting depth, not executed taker flow, trade size, price impact, returns, volatility, cross-market strength, OI, funding or premium.

## Fixed rules

- Data: Binance Vision XRPUSDT USD-M futures daily `bookDepth` snapshots and XRPUSDT spot monthly 1h klines, January 2024–September 2026. Use reported `notional` at percentage -1 (bid) and +1 (ask). No interpolation or invented snapshots.
- From each completed UTC hour use only the 59:30 snapshot, known 30 seconds before the next hour. `log_imbalance=log(bid_notional/ask_notional)`.
- Signal when current log imbalance is at least `log(1.5)` and at or above the linearly interpolated 97.5th percentile of the previous 720 consecutive hourly observations, excluding current.
- Enter spot LONG at the following hourly open with 2 bps adverse slippage. One position only. Causal ATR24; stop 1.5 ATR, target 2R, maximum hold 12 hours. Gap through stop fills at worse open; ambiguous stop/target candle counts as stop.
- Risk 0.5% of current equity to initial stop, capped at 20% notional, no leverage. Fee 9.5 bps per side; stress doubles fee and slippage.

## Validation and gates

2024 is control. Locked quarterly OOS folds are 2025Q1–2026Q3, each flat at $10,000, plus continuous OOS drawdown. Preserve URLs, bytes, local SHA256, gaps, ledgers, tests and independent audit. No retuning after results.

All historical gates must pass: >=150 OOS trades; positive base net/expectancy and PF>1.15; positive stressed net/expectancy and PF>1.02; >=5/7 quarters positive and 2026Q3 positive; continuous base/stress drawdown <=10%; no quarter >35% of all positive-quarter profit. Even a full historical pass remains TEST NEDOKONČEN until >=30 future days and >=100 newly timestamped forward PAPER trades show positive stressed expectancy.

## Pre-result missing-archive amendment — 2026-10-26

The first download stopped on a publisher HTTP 404 before any performance was computed. A missing daily `bookDepth` archive is now recorded explicitly in the manifest and contributes no observations. No depth is interpolated or copied. The existing exact-consecutiveness rule suppresses any 720-hour causal window crossing such a gap. Non-404 download failures remain errors. This ingestion-only amendment is frozen before rerunning and changes no signal, execution, cost, sizing or acceptance parameter.

