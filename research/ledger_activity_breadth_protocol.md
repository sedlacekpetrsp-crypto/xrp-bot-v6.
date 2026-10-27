# XRP_LEDGER_ACTIVITY_BREADTH_V1 — frozen protocol

Preregistered 2026-10-27 before performance evaluation. Offline spot research only.

## Distinct hypothesis

A broadening of genuine XRPL participation should precede price demand: XRP active
addresses per ledger transaction in the upper tail of its own history, together
with above-normal transaction count, should predict positive subsequent XRP spot
returns. This uses on-chain network activity, not OHLC autocorrelation, volume,
aggressor flow, derivatives positioning, market breadth, cross-exchange price,
funding, carry, or order-book depth.

## Frozen rules

- CoinMetrics Community daily XRP `AdrActCnt` and `TxCnt`; Binance Vision
  XRPUSDT daily spot OHLC.
- Activity breadth = `AdrActCnt / TxCnt`.
- A metric dated UTC day D is treated as unavailable throughout D. It may first
  affect the signal at the close of D+1, with entry at the open of D+2. This
  conservative lag prevents same-day aggregate leakage.
- At each signal close, compare the lagged breadth observation with the 80th
  percentile of the preceding 90 lagged daily observations, excluding the
  candidate observation. Also require lagged TxCnt above its preceding 90-day
  median. Exactly 90 consecutive metric and price days are required.
- Long XRPUSDT spot at the next exact daily open. Stop = 2.0 ATR14 below entry;
  target = 2.5 times stop distance; maximum hold 10 daily bars.
- Stop wins an ambiguous stop/target day. A gap through stop fills at the worse
  open. Any data gap suppresses affected histories and closes an open position
  at the last complete close. No missing value is synthesized.
- One position, no overlap. Initial equity $10,000; risk 0.5% current equity,
  notional capped at 20% equity, no leverage.
- Fee 0.095% per side and adverse slippage 0.02% per side; stress doubles both.

## Data and evaluation

Use direct CoinMetrics Community API responses and direct Binance Vision monthly
archives from January 2022 through September 2026. Retain exact URLs, response or
archive byte counts, local SHA256 payload fingerprints, row counts, duplicates,
missing dates and exclusions. Stop on conflicting duplicates or invalid values.

Calendar 2022 is the control. Locked annual OOS folds are 2023, 2024, 2025 and
January-September 2026. A continuous OOS path repeats the same observations and
is descriptive only. No parameter or period selection after results.

All historical gates must pass: at least 80 annual-fold OOS trades; positive net
P/L and expectancy; PF >1.15; positive stressed P/L and expectancy; stressed PF
>1.02; at least three of four OOS years positive at base and stress costs; 2026
positive at both costs; continuous base and stress drawdown <=10%; no calendar
month supplies more than 25% of total positive-month profit.

Historical success alone remains TEST NEDOKONCEN. PROSEL additionally requires
at least 30 future calendar days and 100 new isolated forward PAPER trades with
positive base and stressed expectancy under unchanged rules. Historical failure
means NEPROSEL without retuning.
