# XRP_LABOR_RESILIENCE_V1 — frozen protocol

Preregistered 2026-11-05 before inspecting any historical `ICSA` value or XRP return for this hypothesis. Offline PAPER only.

## Distinct hypothesis and signal

A resilient and improving U.S. labor market can support discretionary risk capacity. Use only the FRED weekly, seasonally adjusted initial unemployment-claims series `ICSA`. An observation is eligible only after two later actual observations. At that point require both: (1) the lagged value is at or below the median of the strictly preceding 52 actual observations; and (2) the mean of the four observations ending at the lagged value is below the mean of the immediately preceding four. Missing observations are excluded and never filled. The signal uses no crypto price, volume, flow, relative strength, volatility, derivatives, on-chain, credit-stock, yield-curve or calendar feature.

## Frozen sources and chronology

- FRED: `https://fred.stlouisfed.org/graph/fredgraph.csv?id=ICSA&cosd=2019-01-01&coed=2026-10-01`.
- Binance Vision public data API: XRPUSDT spot daily OHLC, 2020-01-01 through 2026-09-30 inclusive.
- Retain exact URLs, bytes, rows and SHA256; report gaps and explicit missing values without imputation.
- 2020–2021 is control. Annual-reset OOS folds are 2022, 2023, 2024, 2025 and 2026 through September. The continuous 2022–September 2026 path is descriptive, not independent.

## Frozen execution

Map an eligible weekly observation only to the exact matching UTC XRP date and enter at the next consecutive daily open. ATR(14) uses completed candles through the signal date. Long-only spot; stop 2 ATR below adverse-slippage entry; target 3R; maximum hold five daily bars. Same-bar ambiguity fills stop first; gap through stop fills at the worse open; a data gap exits at the prior close; fold-end liquidates at the last actual close. Base fee is 0.095% per side plus 0.020% adverse slippage per side; stress doubles both. Risk 0.5% of current equity, 20% notional cap, zero leverage, one position, no overlap. Drawdown conservatively marks open positions to each candle low with adverse slippage and an exit fee.

## Frozen acceptance gates

Historical acceptance requires every gate: at least 75 annual OOS trades; positive net and expectancy at base and stress; PF >1.15 base and >1.02 stress; at least four of five folds positive at both costs including 2026; continuous base/stress drawdown <=10%; largest positive month <=25% of total positive-month profit; full tests and independent audit. `PROŠEL` additionally requires at least 30 later calendar days and 100 total independently accrued PAPER trades with positive base and stress expectancy. Historical success alone is `TEST NEDOKONČEN`; any failed historical gate is `NEPROŠEL`. No post-result change to source, direction, lag, windows, hold, costs, folds or gates.

FRED can revise history. The retained hash identifies the evaluated response, not original weekly vintages; the two-observation lag is conservative but cannot reconstruct them.
