# XRP_REALIZED_VALUE_DISCOUNT_V1 — frozen protocol

Preregistered 2026-10-28 before performance evaluation. Offline spot research
only; no production, Render, deployed branch or LIVE change.

## Distinct hypothesis

XRP priced materially below aggregate realized value represents broad holder
unrealized loss and forced-seller exhaustion. Buying a fixed realized-value
discount should earn a recovery premium. This tests a blockchain cost-basis
valuation ratio, not price/volume momentum, market breadth, autocorrelation,
calendar drift, stablecoin supply, network activity/fees, derivatives, order
books, or cross-exchange dislocation.

## Frozen rules

- CoinMetrics Community daily `CapMVRVCur` for XRP and Binance Vision XRPUSDT
  daily spot OHLC, joined only on exact UTC dates.
- A signal occurs when `CapMVRVCur <= 0.90`. The 10% discount is a fixed
  economic buffer below aggregate realized capitalization, not a fitted
  percentile.
- A metric observation dated D is unavailable during D. It may first signal at
  the close of D+1 and enter at the open of D+2. Missing exact dates suppress
  signals; no interpolation or forward fill.
- Long XRPUSDT spot at next exact daily open. Stop 2.0 ATR14 below entry, target
  3.0 times stop distance, maximum hold 30 daily bars.
- Stop wins ambiguous bars; gap-stop fills at worse open. A data gap closes at
  the prior complete close. Fold-end positions liquidate at the last in-fold
  close.
- One position, no overlap. Initial equity $10,000; risk 0.5% current equity;
  notional cap 20% equity; no leverage.
- Fee 0.095% per side and adverse slippage 0.02% per side; stress doubles both.

## Data and evaluation

Use a direct CoinMetrics Community response and direct Binance Vision monthly
archives from January 2020 through September 2026. Preserve URLs, byte counts,
local SHA256 payload fingerprints, row counts, exact gaps, duplicates and
exclusions. Stop on conflicting duplicates or invalid/nonpositive values; never
fabricate data.

Calendar 2020-2021 is the control. Locked annual OOS folds are 2022, 2023, 2024,
2025 and January-September 2026. A continuous OOS path repeats those observations
and is descriptive only. No threshold, exit, holding time or period selection
after results.

All historical gates must pass: at least 75 annual-fold OOS trades; positive net
P/L and expectancy; PF >1.15; positive stressed P/L and expectancy; stressed PF
>1.02; at least four of five OOS years positive at base and stress costs; 2026
positive at both; continuous base and stress drawdown <=10%; no calendar month
supplies more than 25% of total positive-month profit.

Historical success alone remains TEST NEDOKONCEN. PROSEL additionally requires
30 future calendar days and 100 new isolated forward PAPER trades with positive
base and stressed expectancy under unchanged rules. Historical failure means
NEPROSEL without retuning.
