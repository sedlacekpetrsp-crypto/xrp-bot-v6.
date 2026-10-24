# BTC_QUARTERLY_CARRY_V1 preregistration — 2026-10-24

## Distinct hypothesis

Positive basis on a dated BTC quarterly future has a contractual convergence at expiry. When its
annualized premium is at least 8% during the fixed 28-to-7-day pre-expiry window, buy BTC spot and
short equal-notional quarterly futures, holding to expiry unless annualized basis widens to 25%.
This is dated-futures term carry with contractual settlement, not perpetual funding reversal,
perpetual basis dislocation, spot direction, pair z-score or momentum.

## Frozen implementation and execution

- Public Binance Vision BTCUSDT spot and 23 dated USD-M quarterly-contract 1-hour archives,
  March 2021–September 2026. Development expiries: 2021–2023. Untuned validation expiries:
  2024 H1/H2, 2025 H1/H2 and January–September 2026.
- Check only completed 00:00 UTC closes in the entry window; enter the next 01:00 open. Each leg
  is 15% of current equity. No overlapping contracts. Exit at the synchronized 08:00 UTC expiry
  open, or next open after a completed 25% annualized-basis stop. Missing transitions cannot enter.
- Normal per-side fees: spot 0.095%, futures 0.050%; adverse slippage 0.020% per leg and side.
  Stress doubles all fees and slippage. No parameter search follows this preregistration.

## Frozen success criteria

Historical eligibility requires positive normal return in every development year; trades in at
least eight validation expiries; normal PF >= 1.20; stress PF >= 1.05; all five validation blocks
positive normally; at least four positive under stress; positive combined stress return; normal
drawdown <= 5%; and no block over 45% of summed positive P&L. Robust status additionally requires
four new isolated forward PAPER expiries with unchanged rules. A historical pass alone is not
evidence of future profitability.
