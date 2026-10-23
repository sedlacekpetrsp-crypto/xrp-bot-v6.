# WEEKEND_CARRY_V1 preregistration — 2026-10-23

## Distinct hypothesis

Crypto's continuous market may compensate investors for holding systematic spot risk during the
lower-staffed weekend interval. An equal-weight basket held from Saturday 00:00 UTC until Monday
00:00 UTC may therefore earn a repeatable calendar premium after realistic costs. The signal is
purely calendar-based and uses no price trend, flow, sweep, shock, pair spread, cross-sectional
ranking or volatility-sized momentum rule used by previously rejected strategies.

## Frozen rules before historical results

- Universe: BTCUSDT, ETHUSDT, SOLUSDT and XRPUSDT from public Binance spot 1h archives.
- At Saturday 00:00 UTC, buy all four assets at that bar's open; exit at the first open at or
  after 48 elapsed hours. No look-ahead or price-dependent entry filter.
- Allocate 35% of current account equity gross, equally across four legs (8.75% each), with no
  overlapping basket. Each leg has a 6% stop. Stop gaps fill at the worse opening price; otherwise
  a touched stop fills at the stop price.
- Base costs: 0.095% fee and 0.02% adverse slippage per leg and side. Stress doubles both.
- Incomplete days are removed for every symbol; no candle is fabricated. Archive URLs, counts and
  ZIP SHA-256 fingerprints are recorded. Equity and drawdown are marked hourly.

## Chronological protocol and pass criteria

- Development: calendar 2021 and 2022; both must be positive at base costs.
- Untouched validation: 2023, 2024, 2025 and 2026-01-01 through 2026-09-30.
- Validation requires at least 150 completed baskets, combined PF >= 1.15 normally and >= 1.02
  with doubled costs, every block positive normally, at least three of four blocks positive under
  stress, positive combined stressed return, maximum drawdown <= 15%, and no positive block above
  60% of summed positive block P&L.
- Robust-candidate status additionally requires 50 entirely new forward PAPER baskets under the
  frozen rules. A historical pass alone is not evidence of future profitability.

No parameter will be changed after results are observed. Failure retires V1 and does not authorize
optimization of weekdays, entry hour, holding time or stop on these validation blocks.
