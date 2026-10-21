# SOL_ETH_PAIRS_V1 — preregistered protocol

Recorded before downloading or examining performance results for this hypothesis.

## Distinct hypothesis

The log price ratio of SOL to ETH can temporarily diverge from its recent equilibrium and then mean-revert. Trade the ratio as an equal-notional, two-leg pair so most broad crypto direction is hedged. This is cross-asset statistical arbitrage, not a single-asset VWAP/RSI reversal and not a sweep, breakout, order-flow, Fibonacci, Aroon, Supertrend or rotation variation.

## Fixed rules and execution

- Public Binance Vision SOLUSDT and ETHUSDT spot 1-hour archives, November 2022 through September 2026. Hash every archive, verify timestamps and exclude incomplete UTC days from both legs rather than invent candles.
- At each completed hour, calculate the log(SOL/ETH) z-score over the last 720 completed hourly observations. If z >= +2.25, short SOL and long ETH; if z <= -2.25, long SOL and short ETH. Enter both legs at the next hour open.
- Exit both legs at the next open after absolute z falls to 0.40 or less. Stop at absolute z 4.0, after 336 hours, or if either leg moves 12% adversely from its entry. A gap through a leg stop fills both legs at the worse opening prices. Intrabar leg stops use the stop on the triggered leg and that hour's close on its companion.
- One pair position at a time. Gross notional is 35% of current equity, split equally between the legs; no overlapping position and no directional leverage.
- Normal costs per leg: 0.095% fee per side, 0.02% adverse slippage per side and 8% annualized short borrow. Stress doubles fees, slippage and borrow. Equity and drawdown are marked hourly.
- No parameter search or adjustment after historical results are revealed.

## Chronological acceptance gate

Evaluate calendar 2023, 2024, 2025 and January–September 2026 separately, plus the continuous combined path. Reject unless there are at least 50 completed pairs, combined PF >=1.25 normally and >=1.05 under double costs, every block is positive normally, at least three blocks are positive under stress, the combined stressed result is positive, and normal combined maximum drawdown is <=12%.

Passing history alone is not enough. A robust candidate also requires at least 40 new forward PAPER pairs under these exact rules with positive net performance after recorded fees, slippage and borrow. No Render changes, services, existing bot changes or real orders are authorized.
