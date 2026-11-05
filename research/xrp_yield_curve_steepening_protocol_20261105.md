# XRP_YIELD_CURVE_STEEPENING_V1 — frozen protocol

Preregistered 2026-11-05 before any performance evaluation. Offline PAPER
research only; no production, Render, deployed branch or LIVE change.

## Distinct hypothesis

A material steepening of the U.S. Treasury 10-year minus 2-year yield curve can
signal an improving nominal-growth and credit-cycle regime that supports
speculative assets, including XRP. The sole signal input is the external FRED
Treasury spread. It is not an XRP/BTC price, flow, relative-strength,
volatility, derivatives, on-chain, calendar, broad-dollar, absolute-real-yield,
NFCI or reverse-repo rule.

## Frozen rules

- Direct FRED daily `T10Y2Y` (percentage points) and Binance Vision XRPUSDT
  daily spot OHLC. Retain the actual FRED business-day calendar; do not fill
  weekends, holidays or explicit missing values.
- A FRED observation becomes eligible only on the date of the second subsequent
  actual FRED observation. At that eligible UTC close, compare the lagged spread
  with the spread 20 actual FRED observations earlier. Signal when the spread
  has steepened by at least 0.25 percentage point. Negative and positive spread
  levels are both valid. No crypto return enters the signal.
- The 21 required FRED observations must be strictly ordered and finite. The
  signal-date and next XRP calendar-day bars must both exist exactly. No
  interpolation, carry-forward or invented price is permitted.
- Enter long XRPUSDT spot at the next calendar-day open. Stop 2.0 ATR14 below
  entry, target 3.0 times stop distance, maximum hold five daily bars.
- Stop wins an ambiguous bar; a gap through stop fills at the worse open. A
  crypto data gap exits at the prior complete close. Fold-end positions exit at
  the final in-fold close.
- One position, no overlap, zero leverage. Initial equity USD 10,000; risk 0.5%
  current equity; notional cap 20% current equity.
- Fee 0.095% per side plus adverse slippage 0.02% per side. Stress doubles both.

## Data and evaluation

Use direct FRED CSV and direct Binance Vision API data from January 2020 through
September 2026. Retain exact URLs, bytes, local SHA256 fingerprints, row counts,
missing values, duplicates and gaps. Stop on conflicting duplicates or invalid
observations; never fabricate data. FRED can revise history, so the retained
hash identifies the evaluated payload rather than an original publication
vintage.

Calendar 2020–2021 is a descriptive control. Locked annual OOS folds are 2022,
2023, 2024, 2025 and January–September 2026. A continuous OOS path repeats the
same observations and is descriptive only. Do not alter signal, direction,
lag, lookback, exits or dates after results.

Every historical gate must pass: at least 75 annual-fold OOS trades; positive
net P/L and expectancy; PF >1.15; positive doubled-cost net P/L and expectancy;
stress PF >1.02; at least four of five OOS years positive at both costs; 2026
positive at both costs; continuous base and stress drawdown <=10%; no month
provides more than 25% of total positive-month profit; independent audit passes.

Historical success alone remains TEST NEDOKONCEN. PROSEL also requires at least
30 future calendar days and 100 new isolated forward PAPER trades with positive
base and stressed expectancy under unchanged rules. Historical gate failure is
NEPROSEL without inversion, threshold tuning or year selection.

