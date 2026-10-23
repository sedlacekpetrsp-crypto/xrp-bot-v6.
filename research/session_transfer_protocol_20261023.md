# SESSION_TRANSFER_V1 preregistration — 2026-10-23

## Distinct hypothesis

A sufficiently large BTC move during the completed 00:00–07:59 UTC interval may persist during
the 08:00–15:59 UTC interval as liquidity and information transfer between global trading
sessions. This is a single-market, fixed-clock continuation hypothesis, not a weekend premium,
multi-asset shock, order-flow, sweep, pair, cross-sectional rotation or monthly momentum rule.

## Frozen rules before historical results

- Market: BTCUSDT, public Binance spot 1h archives.
- At 08:00 UTC every day, calculate return from the 00:00 open through the 07:00 close using only
  those eight completed, contiguous candles. Enter LONG if return is at least +0.75% or SHORT if
  at most -0.75%; otherwise do nothing. Fill at the 08:00 open with adverse slippage.
- Exit at 2.5% stop, 2.5% target, or the first open at/after eight elapsed hours. Stop wins an
  ambiguous hourly candle. Stop gaps fill at the worse open; favorable target gaps receive only
  the target price.
- One position maximum, sized at 20% of current account equity; no overlap or leverage.
- Base costs: 0.095% fee and 0.02% adverse slippage per side plus 8% annualized borrow on SHORT,
  accrued hourly. Stress doubles all three.
- Remove incomplete UTC days, never fabricate candles, forbid signals across removed days, mark
  equity hourly, and record archive URLs, counts and ZIP SHA-256 fingerprints.

## Chronological protocol and pass criteria

- Development: calendar 2021 and 2022; both must be net positive at base costs.
- Untouched evaluation for this fixed hypothesis: 2023, 2024, 2025 and 2026-01-01 through
  2026-09-30.
- Validation requires at least 300 trades and at least 100 in each direction, combined PF >= 1.20
  normally and >= 1.05 under double costs, every block positive normally, at least three of four
  positive under stress, positive combined stressed return, maximum drawdown <= 15%, and no one
  positive block above 60% of summed positive block P&L.
- Robust-candidate status additionally requires 50 new forward PAPER trades under these frozen
  rules. Historical performance alone is insufficient evidence of future profitability.

Failure retires V1. Do not optimize the session boundary, threshold, bracket or holding interval
on the revealed evaluation blocks.
