# SOL_BASIS_CONVERGENCE_V1 preregistration — 2026-10-24

## Distinct hypothesis

A SOL perpetual premium of at least 0.40% over synchronized spot reflects a temporary futures
dislocation that can converge without taking outright market direction. Enter long spot and
short equal-notional perpetual at the next hourly open; exit after convergence. This two-leg
basis trade is distinct from the rejected directional funding-reversal model and all prior
spot momentum, reversion, volume, range, pair-z-score and calendar families.

## Frozen implementation and execution

- Public Binance Vision SOLUSDT spot 1-hour, USD-M perpetual 1-hour and funding archives,
  December 2020–September 2026. Development: 2021–2023. Untuned validation: 2024 H1/H2,
  2025 H1/H2 and January–September 2026.
- A completed close premium >= 0.40% enters next open. Exit next open after a completed premium
  <= 0.02% target or >= 1.20% stop, or after 48 hours. The next open is the gap fill. Eight-hour
  cooldown; no overlap. Each leg is 15% of current equity (30% gross exposure).
- Normal per-side fees: spot 0.095%, futures 0.050%; adverse slippage 0.020% per leg and side.
  Actual funding on the short perpetual is included. Stress doubles fees/slippage and funding
  debits while halving credits. Missing synchronized hours invalidate that transition.

## Frozen success criteria

Historical eligibility requires positive normal return in every development year; at least 40
continuous-validation trades; normal PF >= 1.20; stress PF >= 1.05; all five validation blocks
positive normally; at least four positive under stress; positive combined stress return; normal
drawdown <= 10%; and no block above 50% of summed positive P&L. Robust status additionally needs
50 new isolated forward PAPER trades under unchanged rules. Backtest passage alone is not proof
of future profitability.
