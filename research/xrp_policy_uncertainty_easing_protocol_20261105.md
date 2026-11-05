# XRP_POLICY_UNCERTAINTY_EASING_V1 — frozen protocol

Preregistered 2026-11-05 before inspecting historical `USEPUINDXD` values or XRP returns for this hypothesis. Offline PAPER only.

## Hypothesis and signal

An easing news-based U.S. economic-policy-uncertainty environment can improve risk-taking capacity. Use only daily FRED `USEPUINDXD`. A value is eligible after two later actual observations. Require the lagged value to be at or below the median of the strictly preceding 90 actual observations and the mean of the five observations ending at that value to be below the immediately preceding five. Missing values are excluded, never filled. This is a news-text uncertainty observable, not crypto price/flow/volume/volatility, VIX, broad financial conditions, labor, credit, rates, calendar, derivatives or on-chain activity.

## Data and chronology

- FRED CSV: `https://fred.stlouisfed.org/graph/fredgraph.csv?id=USEPUINDXD&cosd=2019-01-01&coed=2026-10-01`.
- Binance Vision API XRPUSDT daily spot OHLC, 2020-01-01 through 2026-09-30.
- Retain exact URLs, bytes, rows and SHA256; report gaps and missing values with no imputation.
- Control 2020–2021; annual-reset OOS 2022, 2023, 2024, 2025 and 2026 through September; continuous OOS is descriptive only.

## Execution

An eligible source date must exactly match an XRP UTC date; enter at the next consecutive daily open. ATR(14) uses completed bars. Long-only; stop 2 ATR, target 3R, maximum hold five daily bars. Stop wins same-bar ambiguity; gap-stop fills at worse open; data gap exits prior close; fold-end exits last close. Base fee 0.095% and adverse slippage 0.020% per side; stress doubles both. Risk 0.5% of current equity, notional cap 20%, zero leverage, one position, no overlap. Open positions are conservatively marked to candle lows with adverse exit cost for drawdown.

## Gates

Require at least 75 annual OOS trades; positive base/stress net and expectancy; PF >1.15 base and >1.02 stress; four of five years positive at both costs including 2026; continuous drawdown <=10%; largest positive month <=25% of positive-month profit; full tests and independent audit. `PROŠEL` additionally requires 30 later calendar days and 100 independently accrued PAPER trades with positive base/stress expectancy. Historical success alone is `TEST NEDOKONČEN`; failed history is `NEPROŠEL`. No post-result retuning.

FRED may revise history; retained hashes identify evaluated bytes, not original vintages. The two-observation lag is conservative but cannot reconstruct vintages.
