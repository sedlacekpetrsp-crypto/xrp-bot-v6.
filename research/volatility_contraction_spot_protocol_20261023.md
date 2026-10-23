# VOLATILITY_CONTRACTION_SPOT_V1 preregistration — 2026-10-23

## Distinct hypothesis

A new transition into a sustained BTC volatility-contraction regime may offer positive spot drift
over the following week because leverage and forced liquidation risk have subsided. This is a
long-only, event-triggered variance-regime hypothesis with no SHORT, fixed session, weekday,
price breakout, flow, cross-sectional rank, pair spread or monthly momentum condition.

## Frozen rules before historical results

- Market: BTCUSDT, public Binance spot 1h archives.
- On each completed hourly bar, calculate population standard deviation of log returns over 168
  and 720 contiguous hours. Signal only on a new crossing of the 168h/720h volatility ratio from
  above 0.65 to 0.65 or below. Enter LONG at the next hourly open.
- Allocate 35% of current equity, one position maximum. Exit after 168 elapsed hours or at an 8%
  stop. Enforce a 168-hour cooldown after exit. Stop gaps fill at the worse open.
- Base costs are 0.095% fee and 0.02% adverse slippage per side; stress doubles both.
- Remove incomplete UTC days, prohibit calculations across a gap, fabricate no bars, mark equity
  hourly, and record archive URLs, coverage and ZIP SHA-256 fingerprints.

## Chronological protocol and pass criteria

- Development: 2021 and 2022; both must be positive at base costs.
- Validation: 2023, 2024, 2025 and 2026-01-01 through 2026-09-30.
- Validation needs at least 60 trades, combined PF >= 1.25 normally and >= 1.10 under doubled
  costs, every block positive normally, at least three blocks positive under stress, positive
  combined stressed return, maximum drawdown <= 15%, and no positive block above 60% of summed
  positive block P&L.
- Robust-candidate status additionally requires 30 new forward PAPER trades with frozen rules.
  Historical performance alone is not evidence of future profitability.

Failure retires V1. Do not optimize windows, ratio, holding period, cooldown or stop using the
revealed validation blocks.
