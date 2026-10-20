# CROSS_SECTIONAL_ROTATION_V1 — preregistered protocol

Recorded before downloading or examining results for this hypothesis.

## Distinct hypothesis

Crypto leadership persists across assets during a broad BTC risk-on regime. At each UTC day boundary, rank BTC, ETH, SOL and XRP by their completed 21-day spot return. Hold only the strongest positive-return asset while the last completed BTC daily close is above its 60-day EMA; otherwise hold cash. This is a cross-sectional allocation hypothesis, not a sweep, breakout, order-flow, VWAP-reversion, Fibonacci, Aroon or Supertrend variation.

## Fixed execution and risk parameters

- Source: public Binance Vision spot 15-minute monthly archives, October 2022 through September 2026. Every archive is hashed and every timestamp checked. Exchange-wide outage gaps are recorded, never filled; a UTC day is excluded from all assets unless all four have the complete aligned set of 96 bars.
- Signal: completed daily candles only. Entry or rotation occurs at the next 15-minute open. Ties are deterministic.
- One position across the portfolio, long only, 35% of current account equity; no leverage and no overlapping positions.
- Initial stop: 3.0 times the completed 20-day ATR. A gap through the stop fills at the worse opening price. No same-bar target assumption is needed because there is no profit target.
- Normal costs: 0.095% fee per side plus 0.02% adverse slippage per side. Stress costs double both values.
- No parameter search will be performed after historical results are revealed.

## Chronological evaluation and acceptance gate

Evaluate four untouched-for-this-hypothesis blocks separately: calendar 2023, 2024, 2025 and January–September 2026, plus the combined path. Reject unless all historical conditions pass: at least 80 completed trades; combined profit factor at least 1.20 normally and 1.05 at double costs; every block positive normally; at least three blocks positive under stress; combined stressed return positive; and normal combined maximum drawdown no more than 15%.

Even if every historical gate passes, do not call the strategy robustly profitable and do not deploy it. It must first accumulate at least 30 newly generated forward PAPER trades under the identical rules and remain positive after recorded costs. Existing bots, Render services and real trading are outside this branch and must not be changed.
