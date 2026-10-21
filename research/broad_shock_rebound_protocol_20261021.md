# BROAD_SHOCK_REBOUND_V1 — preregistered protocol

Recorded before downloading or examining performance results for this hypothesis.

## Distinct hypothesis

A synchronized, high-volume six-hour decline across BTC, ETH, SOL and XRP can represent a temporary liquidation shock followed by an 18-hour rebound. Buy a small equal-weight spot basket only after broad price and volume confirmation. This is a cross-market event strategy, not VWAP/RSI reversion, a sweep/breakout, order-flow, Fibonacci, Aroon, Supertrend, relative-strength rotation or pair trade.

## Fixed rules

- Public Binance Vision 1-hour spot archives, September 2020 through September 2026. Hash every archive, verify timestamps and exclude any incomplete UTC day from all four assets without fabricating candles.
- On a completed hour, compute each asset's six-hour close return. A signal requires median return <= -3%, at least three declining assets, and median six-hour mean volume >=1.35 times the immediately preceding 48-hour mean volume.
- Enter BTC, ETH, SOL and XRP equally at the next hourly open. Gross spot notional is 35% of current equity; one basket only, no leverage and no overlap.
- Exit the whole basket after 18 hours. A 6% adverse stop on any leg closes the whole basket. Gaps fill all legs at worse opening prices; an intrabar stop fills the triggered leg at its stop and companions at that hour's close. Wait 12 hours after exit before another entry.
- Normal cost per leg and side is 0.095% fee plus 0.02% adverse slippage. Stress doubles both. Mark equity and drawdown hourly.
- No parameter search or adjustment after historical results are revealed.

## Acceptance gate

Evaluate 2021, 2022, 2023, 2024, 2025 and January–September 2026 separately and as one continuous path. Reject unless there are at least 50 completed baskets, combined PF >=1.20 normally and >=1.05 under double costs, at least five of six blocks are positive normally and four under stress, combined stress return is positive, maximum normal drawdown is <=12%, and no single positive block supplies more than 60% of summed positive block profit.

History alone cannot qualify a robust candidate. It must then produce at least 40 new forward PAPER baskets under identical rules and remain positive after recorded costs. No Render, deployed branch, paused bot or real order changes are authorized.
