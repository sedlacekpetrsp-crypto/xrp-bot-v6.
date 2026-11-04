# BTC_ASSET_MANAGER_ACCUMULATION_XRP_V1 — frozen protocol (2026-11-04)

Status: **PREREGISTERED; PERFORMANCE NOT YET EVALUATED.** Offline research only.

## Distinct hypothesis and source

Persistent accumulation by institutional asset managers in regulated CME Bitcoin futures can identify a broad crypto allocation regime that subsequently spills into XRP. This is not an XRP/BTC relative-price, derivatives-funding, open-interest crowding, exchange-flow, order-book, volume, volatility, macro, calendar, mempool or XRPL-activity strategy. Its sole signal input is the CFTC-disaggregated asset-manager position in the main (not Micro or Nano) CME Bitcoin futures contract, market code `133741`.

Use annual CFTC Traders in Financial Futures futures-only archives for 2018–2026 from `https://www.cftc.gov/files/dea/history/fut_fin_txt_YEAR.zip`. Retain each exact URL, response bytes and local SHA256. From each archive retain rows whose `CFTC_Contract_Market_Code` is exactly `133741`, `FutOnly_or_Combined` is `FutOnly`, and market name is exactly `BITCOIN - CHICAGO MERCANTILE EXCHANGE`. Required fields are report date, open interest, asset-manager long and short positions. Missing/non-numeric required fields, duplicate dates, nonpositive open interest, impossible negative positions, or non-increasing dates are errors; no interpolation or synthetic reports.

## Fixed signal and causal timing

For report `t`, define asset-manager net share as `(long - short) / open_interest`. Require 52 strictly preceding reports. Signal when the current net share is above the ordinary median of those 52 past shares and is also greater than the share four reports earlier. There is no percentile, magnitude or price filter.

CFTC report positions are as of the report date and normally released later in the week. To prevent lookahead, enter only at 00:00 UTC on the first Monday strictly after the report date. This is at least four calendar days after a normal Tuesday report and after its standard Friday release. Any report whose calculated entry is less than four days later is ineligible. Historical files are treated as revised source records, a stated limitation.

## Fixed execution

Buy XRPUSDT spot at that Monday daily open, zero leverage, one position. ATR14 uses preceding closed daily Binance candles. Stop 2 ATR below the adverse entry fill, target 2.5R, maximum seven candles including entry. Stop wins same-candle ambiguity; a stop gap fills at the worse open and an upward target gap is capped at target. Fee 9.5 bps and adverse slippage 2 bps per side; stress doubles both. Risk 0.5% current equity at stop and cap notional at 20%. A price-data gap exits at the last actual pre-gap close. A fold-end position is liquidated at the last real close before the boundary with costs. No synthetic prices, borrowing or funding.

## Locked evaluation and gates

Use actual Binance XRPUSDT daily prices from 2020-01-01 through 2026-09-30. Calendar 2020–2021 is control. Annual-reset OOS folds are 2022, 2023, 2024, 2025 and 2026 through September; a separate continuous OOS path is descriptive. Preserve exact source provenance, the derived CFTC series, complete ledgers and an implementation-independent audit. No tuning follows results.

All historical gates are required: at least 75 annual-fold OOS trades; positive base net/expectancy and PF>1.20; positive double-cost net/expectancy and PF>1.05; at least 4/5 years positive at both costs including 2026; continuous base/stress drawdown <=10%; no exit month >25% of total positive monthly profit; and a passing independent audit of hashes, CFTC contract selection and arithmetic, strict past-only windows, report-to-entry lag, OHLC, ATR, fills, costs, sizing, gaps, non-overlap, equity and reports.

Even a historical pass remains `TEST NEDOKONCEN` until at least 365 future days and 30 newly timestamped forward PAPER trades have positive base and stressed expectancy with unchanged rules and retained source responses. Historical profit and passing code tests never mean `PROSEL`. A completed failed gate means `NEPROSEL`; do not tune the median, four-report direction, holding period or trade direction on these observations.

Next action: commit this protocol, implementation, downloader, audit and tests remotely before downloading XRP performance data. Do not touch production, Render, LIVE, main, paused strategies or `v8-fly-layer-test`.
