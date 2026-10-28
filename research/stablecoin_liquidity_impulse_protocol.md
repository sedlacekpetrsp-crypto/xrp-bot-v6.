# STABLECOIN_LIQUIDITY_IMPULSE_XRP_V1 — frozen protocol

Preregistered 2026-10-28 before performance evaluation. Offline spot research
only; no production, Render, deployed branch or LIVE change.

## Distinct hypothesis

Rapid expansion of aggregate USDT plus USDC circulating supply represents new
crypto-market purchasing liquidity and should precede positive XRP returns. This
tests external stablecoin monetary supply, not XRP on-chain activity, XRP price
or volume momentum, market breadth, derivatives, funding/carry, order books, or
cross-exchange price dislocation.

## Frozen rules

- CoinMetrics Community daily `SplyCur` for USDT and USDC, summed only when
  both assets have an exact UTC date; Binance Vision XRPUSDT daily spot OHLC.
- Liquidity impulse = seven-calendar-day percentage change in combined supply.
- Signal when the lagged impulse is at least +0.50% and at or above the
  deterministic nearest-rank 80th percentile of the preceding 180 consecutive
  seven-day impulses, excluding the candidate observation.
- A supply observation dated D is unavailable during D. It may first signal at
  the close of D+1 and enter at the open of D+2. The seven-day comparison and
  all reference observations must be consecutive; gaps suppress signals.
- Long XRPUSDT spot at next exact daily open. Stop 2.0 ATR14 below entry, target
  3.0 times stop distance, maximum hold 14 daily bars.
- Stop wins ambiguous bars; gap-stop fills at worse open. Data gaps close at the
  prior complete close. Fold-end positions liquidate at the last in-fold close.
- One position, no overlap. Initial equity $10,000; risk 0.5% current equity;
  notional cap 20% equity; no leverage.
- Fee 0.095% per side and adverse slippage 0.02% per side; stress doubles both.

## Data and evaluation

Use direct CoinMetrics Community responses and direct Binance Vision monthly
archives from January 2020 through September 2026. Preserve URLs, byte counts,
local SHA256 payload fingerprints, counts, exact gaps, duplicates and exclusions.
Stop on conflicting duplicates or invalid/nonpositive supply; never fabricate.

Calendar 2020-2021 is the control. Locked annual OOS folds are 2022, 2023, 2024,
2025 and January-September 2026. A continuous OOS path repeats those observations
and is descriptive only. No threshold, asset set, holding time or period selection
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
