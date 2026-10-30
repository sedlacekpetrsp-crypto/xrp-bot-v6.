# BTC_HASHRATE_SHOCK_RECOVERY_XRP_V1 — frozen protocol (2026-10-30)

Status: **PREREGISTERED; PERFORMANCE NOT YET EVALUATED.** Offline research only.

## Distinct hypothesis

A sudden shortfall in estimated Bitcoin network hashrate followed by an immediate recovery can mark temporary miner/network disruption rather than lasting crypto demand destruction. The recovery is hypothesized to precede positive XRP expectancy. This network-security mechanism does not use price direction, relative strength, transaction activity, volume/flow, derivatives, macro, volatility allocation or the closed options family.

## Fixed causal rule

Use direct CoinMetrics Community daily BTC `HashRate`. Preserve the exact URL, response bytes and local SHA256. Require finite positive observations on consecutive UTC dates; do not interpolate. For metric day D, calculate the mean and population standard deviation of the 30 observations D-31 through D-2. Day D-1 is a shock when its hashrate is <= mean minus one standard deviation. Day D confirms recovery only when hashrate D is strictly greater than D-1. Signal on that conjunction. The source day is conservatively considered available after D+1; enter XRPUSDT at D+2 open. The current price and future metric values cannot affect the signal.

## Fixed execution

Long XRP spot, zero leverage, one position. ATR14 uses preceding closed daily XRP candles. Stop two ATR below adverse entry fill, target 3R, maximum seven candles including entry. Stop wins same-candle ambiguity; gap stop fills at the worse open and an upward target gap is capped at target. Fee 9.5 bps and adverse slippage 2 bps per side; stress doubles both. Risk 0.5% current equity at stop and cap notional at 20%. Skip signals during an open position. A price gap exits at the last actual pre-gap close. No synthetic prices, borrowing or funding.

## Locked evaluation and gates

Use actual consecutive Binance XRP daily spot prices January 2020–September 2026. Use 2021 as control, annual OOS folds 2022–2026 through September and a separate continuous OOS diagnostic. Preserve source provenance, all signals/trades and an independent audit. No tuning follows results.

Every historical gate is required: >=120 aggregate annual-fold OOS trades; positive base net/expectancy and PF>1.20; positive double-cost net/expectancy and PF>1.05; >=4/5 years positive at both costs including 2026; continuous base/stress drawdown <=10%; no month >25% of total positive monthly profit; and independent audit of hashes, metric continuity, population statistics, exclusions/current-day recovery, two-day lag, OHLC, ATR, fills, costs, sizing, gap-stop, non-overlap, equity and reports.

Even a historical pass remains `TEST NEDOKONCEN` until >=365 future days and >=30 newly timestamped forward PAPER trades have positive base and stressed expectancy with unchanged rules. Tests and historical profit never mean `PROSEL`. A completed failed gate means `NEPROSEL`; do not change the z threshold, 30-day window or recovery definition on these observations.

Next action: commit this protocol, implementation, downloader, audit and tests remotely before performance; then run unchanged validation. Do not touch production, Render, LIVE, main, paused strategies or `v8-fly-layer-test`.
