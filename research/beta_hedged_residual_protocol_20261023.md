# BETA_HEDGED_RESIDUAL_MOMENTUM_V1 preregistration — 2026-10-23

## Distinct hypothesis and fixed rules

Altcoin returns unexplained by contemporaneous BTC beta may persist for ten more days. At each
UTC day boundary, use 60 completed daily log returns to estimate each ETH, SOL and XRP beta to
BTC (clamped to 0.25–2.50). Sum the last ten daily residual returns. If absolute residual is at
least 5%, select the largest absolute residual: long the alt and short beta-weighted BTC for a
positive residual, or short the alt and long beta-weighted BTC for a negative residual.

Enter at the next 00:00 UTC hourly open. Split 35% gross exposure between the alt and BTC in
1:beta proportions. Hold at most 240 hours, enforce a 120-hour cooldown, and exit both legs if
either hits a 10% adverse stop. Stop gaps fill at worse opens; for an intrabar stop the triggering
leg fills at its stop and the co-leg at its adverse hourly extreme. Only one pair may exist.

Base costs are 0.095% fee and 0.02% adverse slippage per leg and side plus 8% annualized borrow on
the short leg; stress doubles all three. Incomplete days are removed across all symbols, windows
cannot cross gaps, no candle is fabricated, equity is marked hourly, and archive URLs, counts and
ZIP SHA-256 fingerprints are retained.

## Chronological protocol and gates

- Development: 2021 and 2022, both positive normally.
- Validation: 2023, 2024, 2025 and 2026-01-01 through 2026-09-30.
- Require at least 80 validation pairs and at least 20 in each residual direction, combined PF
  >=1.25 normally and >=1.10 under double costs, every block positive normally, at least three
  blocks positive under stress, positive combined stress, maximum drawdown <=15%, and no positive
  block above 60% of positive block P&L.
- Robust status additionally requires 30 new forward PAPER pairs under frozen rules.

This is residual continuation, not SOL/ETH z-score mean reversion or unhedged winner rotation.
Failure retires V1 without tuning beta windows, residual threshold, stops or holding time.
