# XRP_FLOAT_EXPANSION_SLOWDOWN_V1 — frozen protocol (2026-10-30)

Status: **PREREGISTERED; PERFORMANCE NOT YET EVALUATED.** Offline research only.

## Distinct hypothesis

`CapMrktEstUSD / CapMrktCurUSD` cancels the shared XRP price and proxies CoinMetrics' estimated circulating-supply fraction relative to current/full supply. A low relative pace of 30-day float expansion is hypothesized to represent reduced token-distribution overhang and positive subsequent XRP expectancy. This tokenomics mechanism is distinct from holder-count growth, market-value/realized-value valuation, stablecoin supply, transaction activity/composition, price/volume/flow, derivatives, macro, developer, cadence and protocol-event hypotheses.

## Fixed causal signal

Use direct CoinMetrics Community daily XRP `CapMrktEstUSD` and `CapMrktCurUSD`; retain raw URL, bytes and SHA256. Keep exact consecutive dates where both are finite and positive from the first estimated-cap observation. Do not interpolate. For day D, define float fraction `estimated/current` and its 30-calendar-day change in percentage points. Compare the current change with the nearest-rank 20th percentile of the preceding 365 such 30-day changes, excluding D. Signal when current change is <= threshold. Day D is conservatively available after D+1; enter XRPUSDT at D+2 open. No price level, return, holder, activity, or absolute capitalization filter selects signals.

## Fixed execution

Long XRP spot only, zero leverage, one position. ATR14 using preceding closed daily candles; stop 2 ATR below adverse entry fill; target 3R; maximum 10 candles including entry. Stop wins same-candle ambiguity and a stop gap fills at worse open. Fee 9.5 bps and slippage 2 bps each side; stress doubles both. Risk 0.5% current equity at stop, capped at 20% notional. Skip signals during positions. A data gap exits at last actual pre-gap close; no synthetic prices.

## Locked evaluation and gates

Use actual Binance Vision XRP daily archives January 2020–September 2026. Because the metric begins in June 2019 and needs 395 days of warm-up, use 2021 as control; annual OOS folds 2022–2026 through September and a separate continuous OOS diagnostic. Preserve complete source hashes, gaps, ledgers and independent audit. No tuning after results.

Historical gates: >=120 aggregate OOS trades; positive base net/expectancy and PF>1.20; positive double-cost net/expectancy and PF>1.05; >=4/5 years positive at both costs including 2026; continuous base/stress drawdown <=10%; no month >25% of positive monthly profit; independent audit passes hashes, price-cancelling ratio, past-only nearest-rank arithmetic and lag, chronology, fills, costs, sizing, non-overlap, equity and reports.

Even a complete historical pass remains `TEST NEDOKONČEN` until >=30 future days and >=100 newly timestamped forward PAPER trades show positive stressed expectancy. Historical results or tests alone never mean `PROŠEL`. Failed completed gates mean `NEPROŠEL`; do not alter 30/365 windows or percentile on these dates.

Next action: commit this protocol, code and mechanics tests remotely before performance; then run unchanged validation and independent audit.
