# XRP_CROSS_EXCHANGE_RESIDUAL_CONVERGENCE_V1 — frozen protocol

Preregistered 2026-10-27 before any performance evaluation. This is an offline,
market-neutral research candidate, not a production or LIVE strategy.

## Distinct hypothesis

Coinbase XRP/USD can temporarily trade below Binance XRPUSDT perpetual after
removing the contemporaneous Coinbase-vs-Binance BTC/USD basis. The residual
discount should converge. This tests a second-exchange relative-price
dislocation, not XRP momentum, candle volume, aggressor flow, funding/carry,
open interest, market breadth, or a single-exchange spot/perpetual premium.

## Frozen signal and execution

- Hourly closed bars, exact UTC timestamp intersection only.
- Residual at a closed hour:
  `(Coinbase XRPUSD close / Binance XRPUSDT mark close) /
  (Coinbase BTCUSD close / Binance BTCUSDT spot close) - 1`.
- Enter only when residual is at or below -0.75%.
- At the next exact hourly open, buy Coinbase XRP/USD spot and short equal USD
  notional of Binance XRPUSDT perpetual. One pair position; no overlap.
- Exit at the next open after a closed-hour residual reaches -0.10% or higher,
  after 72 hours, or immediately at an adverse residual of -1.75%.
- A stop crossed at the bar open fills at that worse open. Intrabar stop testing
  uses the conservative executable extreme: Coinbase XRP low, Binance XRP mark
  high, Coinbase BTC high, Binance BTC low. Stop wins over convergence/time.
- Any required-data gap closes the pair at the last complete close; signals and
  positions never cross a gap. Missing candles are never synthesized.
- Initial equity $10,000. Each leg is capped at 10% of current equity (20% gross
  exposure); nominal stop risk is therefore below 0.5% before costs. Zero net
  XRP direction is targeted; no leverage beyond the short derivative leg.
- Include actual Binance short-leg funding cashflows at published nominal times.
- Base costs per fill: Coinbase taker fee 0.60%, Binance perpetual fee 0.05%,
  adverse slippage 0.10% Coinbase and 0.03% Binance. Stress doubles every fee
  and slippage assumption. No maker-fill assumption.

## Data and chronology

- Direct Coinbase Exchange public candles for XRP-USD and BTC-USD; direct
  Binance Vision XRPUSDT mark-price, BTCUSDT spot, and XRPUSDT funding archives.
- Evaluation begins only where all required series exist. Expected Coinbase XRP
  suspension gaps are retained, not backfilled. URLs, byte payload hashes
  (SHA256), counts, duplicates and exact gaps must be written to results.
- H2 2023 is a control period. Locked OOS folds are calendar quarters from
  2024-Q1 through 2026-Q3. A separate continuous OOS path is descriptive and
  repeats the same observations; it is not added to the fold sample.
- Parameters are fixed globally. No threshold, fee, holding-period, venue, or
  period selection after seeing returns.

## Frozen historical gates

All must pass: at least 120 annual-fold OOS trades; positive OOS net P/L and
expectancy; PF >1.15; positive stressed net P/L and expectancy; stressed PF
>1.02; at least 7 of 11 OOS quarters positive at base and stress costs; 2026-Q3
positive at both costs; continuous base and stress drawdown <=10%; no single
quarter supplies more than 30% of total positive-quarter profit. The control is
reported but is not optimized.

Even if every historical gate passes, status remains TEST NEDOKONCEN until at
least 30 future calendar days and 100 new, timestamped, isolated forward PAPER
trades also have positive base and stressed expectancy with the same frozen
rules. Only then may the candidate be called PROSEL. Historical failure means
NEPROSEL without retuning.
