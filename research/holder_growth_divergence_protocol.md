# XRP_HOLDER_GROWTH_DIVERGENCE_V1 — frozen protocol

Preregistered 2026-10-28 before performance evaluation. Offline spot research
only; no production, Render, deployed branch or LIVE change.

## Distinct hypothesis

A growing count of XRP ledger addresses with a nonzero balance during a material
30-day price decline indicates continued holder-base adoption while price is
under pressure. This fundamental/price divergence should earn a subsequent
recovery premium. It tests stock ownership breadth, not transaction/active-
address activity, fees, price-only relative strength, stablecoin supply, MVRV
valuation, derivatives, order books, volume flow or cross-exchange dislocation.

## Frozen rules

- CoinMetrics Community daily `AdrBalCnt` for XRP and Binance Vision XRPUSDT
  daily spot OHLC, joined only on exact UTC dates.
- At close D, signal when the latest usable metric dated D-1 has grown at least
  1.0% from D-31 and XRP close has fallen at least 10.0% from D-30 to D.
  Both are fixed 30-calendar-day economic thresholds, not fitted percentiles.
- The full 32-date metric/price window and the next entry date must be exactly
  consecutive. Missing dates suppress the signal; no interpolation or forward
  fill.
- Enter long XRPUSDT spot at D+1 open. Stop 2.0 ATR14 below entry, target 3.0
  times stop distance, maximum hold 30 daily bars.
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
