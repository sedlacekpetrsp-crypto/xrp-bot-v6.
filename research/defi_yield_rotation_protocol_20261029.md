# DEFI_YIELD_ROTATION_XRP_V1 — preregistration (2026-10-29)

Status: HYPOTHESIS REGISTERED; PERFORMANCE NOT YET EVALUATED. This document is not evidence of profitability.

## Distinct hypothesis

A persistent fall in the realized supply APY of the largest plain USDC pool on Aave v3 Ethereum reduces the observable opportunity cost of holding a non-yielding crypto asset. The candidate buys XRP spot only when the pool APY is both below its trailing median and has fallen materially over the last week. This is a DeFi capital-allocation hypothesis based on an external lending market, not a variation of the rejected XRP price/volume/flow, sentiment, relative-strength, stablecoin-supply, funding, macro-rate, VIX, or financial-conditions strategies.

No pool, threshold, lookback, exit, or test period may be changed after this commit on the basis of returns.

## Frozen data and alignment

- Yield source: DefiLlama public yields API, pool `aa70268e-4b52-42bf-a116-608b370f9501`, Aave v3, Ethereum, USDC, single-asset exposure.
- Discovery endpoint: `https://yields.llama.fi/pools`; history endpoint: `https://yields.llama.fi/chart/aa70268e-4b52-42bf-a116-608b370f9501`.
- Pool is selected before performance evaluation as the highest-TVL ordinary Aave v3 Ethereum USDC pool in the discovery snapshot; Umbrella, Prime and Horizon variants are excluded.
- Price source: actual Binance Vision `XRPUSDT` spot daily kline ZIP archives.
- Store exact URLs, retrieval timestamps, raw SHA256 hashes, row counts, timestamp coverage and gaps. Never fabricate or forward-fill missing yield or price observations.
- Sort and deduplicate yield timestamps. A yield observation may create an order only at the first XRP daily open strictly after its source timestamp. All rolling features use that observation and earlier observations only.
- Binance OHLCV timestamps must be unique and increasing. Missing daily candles invalidate any signal whose ATR warmup or trade path crosses the gap.

## Frozen signal and execution

For each yield observation after 30 valid observations exist:

1. `apy <= median(last 30 APY observations, including current)`;
2. `apy - apy[-7] <= -0.50` percentage points.

If both hold, schedule a long entry at the first later XRP daily open. Duplicate source observations mapping to the same entry open collapse to one signal. Only one position may be open; signals while in a position are ignored. There is no shorting, leverage, pyramiding, pool substitution, reward-APY addition, or parameter search.

- ATR(14) from fully closed XRP daily candles available before entry.
- Entry: scheduled open plus adverse slippage.
- Stop: entry minus 2.0 ATR.
- Target: entry plus 3.0 times initial stop distance.
- Maximum holding: 10 daily bars, exiting at the tenth close.
- Intrabar stop/target ambiguity: stop wins.
- Gap through stop: worse daily open plus adverse exit slippage; gap through target does not receive a better-than-target fill.
- Fee: 0.095% per side; adverse slippage: 0.02% per side.
- Stress: double both fee and slippage.
- Starting equity: USD 10,000 per independent fold.
- Size: risk 0.5% of current equity to initial stop before costs, capped at 20% of equity notional; zero leverage.
- Costs are charged on actual entry and exit notionals. Equity and drawdown include realized costs. No overlapping positions.

## Frozen chronology and acceptance gates

Source feasibility/training-only period: 2023-02-06 through 2023-12-31. Locked exploratory OOS folds: calendar 2024, calendar 2025, and 2026 through the last complete available Binance monthly archive. Each annual fold starts flat with USD 10,000; a separate continuous OOS run is descriptive and not independent evidence. No repeated tuning against these already-inspected market years is allowed.

Historical promotion requires all of:

- at least 75 aggregate annual-fold OOS trades;
- positive aggregate net P/L and expectancy at base and double costs;
- aggregate PF > 1.20 base and > 1.05 stress;
- every OOS calendar fold with trades positive at base and stress;
- maximum drawdown <= 10% at base and stress;
- no single calendar month supplies more than 50% of positive aggregate profit;
- independent audit passes chronology, exact source-to-entry timing, no overlap, sizing/caps, costs, gap-stop, equity reconciliation, data hashes and gap handling.

Even if every historical gate passes, the strategy remains only a forward-PAPER candidate. `PROŠEL` additionally requires at least 30 later calendar days and 75 new timestamped, independently accrued forward-PAPER trades with positive base and stressed expectancy and no methodology change. No historical replay counts as forward evidence.

## Next action

Commit a source-feasibility record, then implement mechanics and tests. Download raw sources, run unit tests, annual and continuous OOS simulations, double-cost stress and an independent audit. Save full results and trade ledgers. Do not change production, Render, main, `v8-fly-layer-test`, paused strategies, or LIVE trading.
