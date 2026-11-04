# BTC_MEMPOOL_CLEARANCE_XRP_V1 — frozen protocol (2026-11-04)

Status: **PREREGISTERED; PERFORMANCE NOT YET EVALUATED.** Offline research only.

## Distinct hypothesis and source

Unusually low Bitcoin settlement congestion can reflect available block-space capacity and lower payment friction, a risk-capacity environment that may precede positive weekly expectancy in high-beta XRP. This is not a price, relative-strength, volume, order-book, flow, derivatives, macro, XRP activity-count, hashrate/security or calendar-drift signal. The signal uses only Bitcoin mempool backlog magnitude and a fixed weekly observation schedule.

Use Blockchain.com Charts `mempool-size` at `https://api.blockchain.info/charts/mempool-size?start=2019-01-01&timespan=2830days&format=json&sampled=false`. Retain the exact response URL, bytes and local SHA256. Deduplicate no timestamps: any duplicate or non-increasing timestamp is an error. Aggregate by UTC date using the median of the original intraday byte observations. A day is valid only with at least 64 unique observations (two thirds of the expected 96); any fewer is an explicit failure, not an interpolation. The frozen query covers 2019-01-01 through the first 2026-10-01 point; exclude timestamps on or after 2026-10-01.

## Fixed signal and causal timing

Consider Friday UTC days only. Compare the Friday daily median with the empirical lower tercile of the strictly preceding 365 consecutive valid daily medians. The lower-tercile cutoff is the sorted zero-based element `(365-1)//3 = 121`, with no interpolation. Signal when Friday is less than or equal to that cutoff. Enter XRP only at Monday 00:00 UTC open, exactly three timestamp-days later and a full 48 hours after Friday has closed. Current/future XRP prices cannot affect the signal. No second indicator, magnitude threshold or parameter search is allowed.

## Fixed execution

Long XRPUSDT spot, zero leverage, one position. ATR14 uses preceding closed daily Binance candles. Stop two ATR below adverse entry fill, target 3R, maximum five candles including entry. Stop wins same-candle ambiguity; a stop gap fills at the worse open and an upward target gap is capped at target. Fee 9.5 bps and adverse slippage 2 bps per side; stress doubles both. Risk 0.5% current equity at stop and cap notional at 20%. A price-data gap exits at the last actual pre-gap close. No synthetic prices, borrowing or funding.

Post-first-run correctness clarification, committed before rerun: an audit exposed that a position opened during a fold's final partial week contributed mark-to-market drawdown but was silently omitted from trades and realized PnL. This invalidates the first output. The corrected simulator liquidates any such position at the last real candle close strictly before the fold boundary, charges normal exit slippage and fees, and records reason `FOLD_END`. Signal, source, parameters, gates and date ranges are unchanged. Only the corrected rerun may be evaluated.

## Locked evaluation and gates

Use actual Binance XRPUSDT daily prices from 2020-01-01 through 2026-09-30. Calendar 2020–2021 is control. Annual-reset OOS folds are 2022, 2023, 2024, 2025 and 2026 through September; a separate continuous OOS path is descriptive. Preserve derived daily metrics, exact source provenance, all trade ledgers and an implementation-independent audit. No tuning follows results.

All historical gates are required: at least 75 annual-fold OOS trades; positive base net/expectancy and PF>1.20; positive double-cost net/expectancy and PF>1.05; at least 4/5 years positive at both costs including 2026; continuous base/stress drawdown <=10%; no month >25% of total positive monthly profit; and a passing independent audit of hashes, intraday uniqueness/counts, daily medians, consecutive dates, strict past-only tercile, Friday/Monday timing, OHLC, ATR, fills, costs, sizing, gaps, non-overlap, equity and reports.

Even a historical pass remains `TEST NEDOKONCEN` until at least 365 future days and 30 newly timestamped forward PAPER trades have positive base and stressed expectancy with unchanged rules and retained source responses. Historical profit and passing code tests never mean `PROSEL`. A completed failed gate means `NEPROSEL`; do not tune the tercile, weekday, 365-day window or direction on these observations.

Next action: commit this protocol, implementation, downloader, audit and tests remotely before downloading XRP performance data. Do not touch production, Render, LIVE, main, paused strategies or `v8-fly-layer-test`.
