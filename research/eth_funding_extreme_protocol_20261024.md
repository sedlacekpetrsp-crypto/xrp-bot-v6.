# ETH_FUNDING_EXTREME_REVERSAL_V1 preregistration — 2026-10-24

## Distinct hypothesis

An unusually large perpetual funding rate identifies crowded leveraged positioning that may
mean-revert over the following day. After a completed ETHUSDT funding settlement with absolute
rate at least 0.020%, enter against its sign at the following hourly open. This uses a new
derivatives data source and carry/crowding mechanism, not a variation of rejected spot flow,
volume, trend, range, session, pair or portfolio signals.

## Frozen implementation and execution

- Public Binance Vision ETHUSDT USD-M perpetual 1-hour klines and funding-rate monthly archives,
  December 2020–September 2026. Development: 2021, 2022, 2023. Validation: 2024 H1/H2,
  2025 H1/H2 and January–September 2026; validation is not used for parameter tuning.
- Funding is acted on only at the open one full hourly timestamp later. No overlapping positions.
  Archive settlement timestamps up to one second after their nominal hour are normalized back to
  that hour; larger offsets are rejected rather than silently shifted.
- Position is 20% of current equity; 5% adverse stop, 3% target, 24-hour maximum hold and eight-hour
  cooldown. Same-bar ambiguity is a stop; a stop gap fills at the worse open.
- Normal per-side taker fee 0.050% and adverse slippage 0.020%. Actual intervening funding cashflows
  are included. Stress doubles fees/slippage and funding debits while halving funding credits.

## Frozen success criteria

Historical eligibility requires all of: positive normal return in all three development years;
at least 80 validation trades; each direction at least 20% of the sample; normal PF >= 1.20;
stress PF >= 1.05; every validation block positive normally; at least four of five positive under
stress; positive combined stress return; normal drawdown <= 15%; and no block above 50% of summed
positive validation P&L. Robust-candidate status additionally requires 50 new isolated forward
PAPER trades with unchanged rules. A historical pass alone is not evidence of future profit.
