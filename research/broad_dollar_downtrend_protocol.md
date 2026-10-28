# XRP_BROAD_DOLLAR_DOWNTREND_V1 — frozen protocol

Preregistered 2026-10-28 before performance evaluation. Offline spot research
only; no production, Render, deployed branch or LIVE change.

## Distinct hypothesis

Persistent weakening of the Federal Reserve broad trade-weighted U.S. dollar
index eases global dollar financial conditions and should create a risk-asset
tailwind for XRP. This tests an external fiat macro variable, not crypto price
relative strength, market breadth, stablecoin supply, on-chain activity or
valuation, derivatives, order books, volume flow, calendar drift or exchange
dislocation.

## Frozen rules

- Federal Reserve FRED daily `DTWEXBGS` and Binance Vision XRPUSDT daily spot
  OHLC. FRED observations retain their published business-day calendar; weekends
  and holidays are not filled.
- A dated FRED value becomes eligible only on the date of the second subsequent
  actual FRED observation. At that eligible UTC close, calculate the 20-
  observation percentage change ending at the lagged value. Signal when it is
  at or below -1.5%. No XRP return or crypto indicator enters the signal.
- The 21 required FRED observations must be strictly increasing, finite and
  positive. The signal-date and next XRP daily bars must exist exactly; no
  interpolation or forward fill.
- Enter long XRPUSDT spot at the next calendar-day open. Stop 2.0 ATR14 below
  entry, target 3.0 times stop distance, maximum hold 10 daily bars.
- Stop wins ambiguous bars; gap-stop fills at worse open. A crypto data gap
  closes at the prior complete close. Fold-end positions liquidate at the last
  in-fold close.
- One position, no overlap. Initial equity $10,000; risk 0.5% current equity;
  notional cap 20% equity; no leverage.
- Fee 0.095% per side and adverse slippage 0.02% per side; stress doubles both.

## Data and evaluation

Use the direct FRED CSV and direct Binance Vision monthly archives from January
2020 through September 2026. Preserve URLs, byte counts, local SHA256 payload
fingerprints, row counts, exact gaps, duplicates and exclusions. Stop on
conflicting duplicates or invalid/nonpositive values; never fabricate data.

Calendar 2020-2021 is the control. Locked annual OOS folds are 2022, 2023, 2024,
2025 and January-September 2026. A continuous OOS path repeats those observations
and is descriptive only. No threshold, lag, exit, holding time or period
selection after results.

All historical gates must pass: at least 75 annual-fold OOS trades; positive net
P/L and expectancy; PF >1.15; positive stressed P/L and expectancy; stressed PF
>1.02; at least four of five OOS years positive at base and stress costs; 2026
positive at both; continuous base and stress drawdown <=10%; no calendar month
supplies more than 25% of total positive-month profit.

Historical success alone remains TEST NEDOKONCEN. PROSEL additionally requires
30 future calendar days and 100 new isolated forward PAPER trades with positive
base and stressed expectancy under unchanged rules. Historical failure means
NEPROSEL without retuning.
