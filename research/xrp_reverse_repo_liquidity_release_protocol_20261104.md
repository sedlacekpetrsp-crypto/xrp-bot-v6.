# XRP_REVERSE_REPO_LIQUIDITY_RELEASE_V1 — frozen protocol

Preregistered 2026-11-04 before any performance evaluation. Offline spot
research only; no production, Render, deployed branch or LIVE change.

## Distinct hypothesis

A rapid decline in cash parked in the Federal Reserve's overnight reverse-repo
facility can represent a release of dollar liquidity from a monetary-policy
drain. That release may support subsequent speculative-asset demand and XRP
spot returns. The sole signal input is the external FRED RRP balance; no XRP,
BTC, volume, order flow, derivative, relative-strength, volatility, sentiment,
calendar, on-ledger or previously tested rates/dollar-index feature enters it.

## Frozen rules

- Direct FRED daily `RRPONTSYD` and Binance Vision XRPUSDT daily spot OHLC.
  FRED observations retain their published business-day calendar; weekends and
  holidays are not filled or carried forward.
- A FRED observation becomes eligible only on the date of the second subsequent
  actual FRED observation. At that eligible UTC close, compare the lagged value
  with the value 20 actual FRED observations earlier. Signal only when the
  earlier balance is at least USD 100 billion and the percentage decline is at
  least 10% (`latest / earlier - 1 <= -0.10`). These economically fixed levels
  are not selected from XRP returns.
- All 21 required FRED observations must be strictly ordered and finite; the
  earlier value must be positive and the latest nonnegative. The signal-date
  and next XRP calendar-day bars must exist exactly. No interpolation,
  imputation or invented price is allowed.
- Enter long XRPUSDT spot at the next calendar-day open. Stop 2.0 ATR14 below
  entry, target 3.0 times stop distance, maximum hold five daily bars.
- Stop wins an ambiguous bar; a gap through stop fills at the worse open. A
  crypto data gap liquidates at the prior complete close. Fold-end positions
  liquidate at the final in-fold close.
- One position, no overlap, zero leverage. Initial equity USD 10,000; risk 0.5%
  of current equity; notional cap 20% of current equity.
- Fee 0.095% per side plus adverse slippage 0.02% per side. Stress doubles both.

## Data and evaluation

Use the direct FRED CSV and official Binance Vision monthly archives from
January 2020 through September 2026. Retain exact URLs, byte counts, local
SHA256 payload fingerprints, rows, missing FRED values, duplicates and price
gaps. Stop on conflicting duplicates or invalid observations; never fabricate
data. FRED history may be revised, so the retained payload hash identifies the
evaluated download but is not a point-in-time vintage guarantee.

Calendar 2020–2021 is a descriptive control. Locked annual OOS folds are 2022,
2023, 2024, 2025 and January–September 2026. A continuous OOS path repeats the
same observations and is descriptive, not independent evidence. Do not alter
the threshold, lag, lookback, direction, exits or dates after results.

Every historical gate must pass: at least 75 annual-fold OOS trades; positive
net P/L and expectancy; PF >1.15; positive doubled-cost net P/L and expectancy;
stress PF >1.02; at least four of five OOS years positive at both costs; 2026
positive at both costs; continuous base and stress drawdown <=10%; no calendar
month provides more than 25% of total positive-month profit; independent audit
passes.

Historical success alone remains TEST NEDOKONCEN. PROSEL additionally requires
at least 30 future calendar days and 100 new isolated forward PAPER trades with
positive base and stressed expectancy under unchanged rules. Historical gate
failure means NEPROSEL without inversion, threshold tuning or year selection.

