# BNB_VOLUME_DRYUP_V1 preregistration — 2026-10-24

## Distinct hypothesis

After a material 48-hour BNB decline, a sharp contraction in recent quote volume can indicate
seller exhaustion. Buy BNB spot only when the completed 48-hour return is at most -3% and mean
quote volume over the last six completed hours is at most 70% of the preceding 48-hour mean.
This is a single-asset supply-exhaustion event on a new market, not the rejected cross-market
shock rebound, flow pressure, sweep trend, range-limit, pair or portfolio-momentum families.

## Frozen implementation and execution

- Public Binance Vision `BNBUSDT` spot 1-hour monthly archives, November 2020–September 2026.
- Development: calendar years 2021, 2022 and 2023. Validation, never used to tune parameters:
  2024 H1, 2024 H2, 2025 H1, 2025 H2 and January–September 2026.
- Signal uses completed bars only; entry is the next hourly open. Any gap inside required history
  invalidates the signal. No overlapping position is permitted.
- Long 25% of current equity; 4% stop, 6% target, maximum 36-hour hold and 24-hour cooldown after
  exit. Ambiguous same-bar stop/target resolves to stop; a stop gap fills at the worse open.
- Normal per-side fee 0.095% and adverse slippage 0.02%. Stress doubles both. No parameter search.

## Frozen success criteria

Historical eligibility requires all of: positive normal return in all three development years;
at least 80 continuous-validation trades; normal PF >= 1.20; double-cost PF >= 1.05; every
validation block positive normally; at least four of five positive under stress; positive
combined stress return; normal drawdown <= 15%; and no block supplying more than 50% of summed
positive validation P&L. Robust-candidate status additionally requires 50 new isolated forward
PAPER trades under the same rules. A historical pass alone is not evidence of future profit.
