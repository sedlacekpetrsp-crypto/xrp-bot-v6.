# XRP_NETWORK_FEE_PRESSURE_V1 — frozen protocol

Preregistered 2026-10-27 before any performance evaluation. Offline spot research
only; no production, Render, deployed branch or LIVE change.

## Distinct hypothesis

High XRP fees burned per successful value-transfer transaction identify urgent
ledger demand and should precede short-horizon positive XRP returns. This tests
network fee pressure, not active-address breadth, price/volume momentum,
aggressor flow, derivatives positioning, funding/carry, order-book depth or
cross-exchange price dislocation.

## Frozen rules

- CoinMetrics Community daily XRP `FeeTotNtv` and `TxTfrCnt`; Binance Vision
  XRPUSDT daily spot OHLC.
- Fee pressure = `FeeTotNtv / TxTfrCnt` XRP burned per transfer.
- A metric dated day D is unavailable during D. It may first signal at the close
  of D+1 and enter at the open of D+2.
- Signal when lagged fee pressure is at or above the deterministic nearest-rank
  85th percentile of the preceding 90 consecutive lagged daily observations,
  excluding the candidate day. Nearest rank is `ceil(0.85 * 90)`, one-based.
- Long XRPUSDT spot at the next exact daily open. Stop 1.5 ATR14 below entry,
  target 2.0 times stop distance, maximum hold 5 daily bars.
- Stop wins an ambiguous bar; a gap through stop fills at the worse open. A data
  gap suppresses affected histories and closes an open position at the last
  complete close. Fold-end positions are liquidated at the last in-fold close.
- One position, no overlap. Initial equity $10,000; risk 0.5% current equity;
  notional capped at 20% equity; no leverage.
- Fee 0.095% per side and adverse slippage 0.02% per side; stress doubles both.

## Data and evaluation

Use direct CoinMetrics Community responses and direct Binance Vision monthly
archives, January 2022 through September 2026. Preserve URLs, byte counts, local
SHA256 payload fingerprints, row counts, duplicates, gaps and exclusions. Stop
on conflicting duplicates or invalid/nonpositive metrics; never fabricate data.

Calendar 2022 is control. Locked OOS folds are 2023, 2024, 2025 and
January-September 2026. A continuous OOS path is descriptive and repeats the
same observations. No threshold, metric, holding period or period selection
after performance is seen.

All historical gates must pass: at least 100 annual-fold OOS trades; positive net
P/L and expectancy; PF >1.15; positive stressed P/L and expectancy; stressed PF
>1.02; at least three of four OOS years positive at base and stress costs; 2026
positive at both costs; continuous base and stress drawdown <=10%; no calendar
month supplies more than 25% of total positive-month profit.

Historical success alone remains TEST NEDOKONCEN. PROSEL additionally requires
30 future calendar days and 100 new isolated forward PAPER trades with positive
base and stressed expectancy under unchanged rules. Historical failure means
NEPROSEL without retuning.
