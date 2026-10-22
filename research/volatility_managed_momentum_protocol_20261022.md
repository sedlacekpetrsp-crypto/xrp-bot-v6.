# VOLATILITY_MANAGED_MOMENTUM_V1 — preregistered protocol

Recorded before downloading or examining performance results for this hypothesis.

## Distinct hypothesis

Medium-term positive absolute momentum can persist, while inverse-volatility weights reduce concentration in the most unstable coins. At each calendar month boundary, hold only BTC, ETH, SOL and XRP assets with positive completed 90-day returns. Weight eligible assets by inverse completed 30-day realized volatility. This is a monthly multi-asset allocation rule, not a breakout/sweep, liquidation event, order-flow, VWAP/RSI reversion, relative-strength winner rotation or pair trade.

## Fixed execution and risk

- Public Binance Vision 1-hour spot archives, September 2020 through September 2026. Hash every archive, verify timestamps and exclude incomplete UTC days from every asset without fabricating candles.
- Signals use completed daily closes only. At the first hourly open of each UTC month, close old legs, then buy eligible legs. Total gross allocation is at most 35% of current equity. Raw inverse-volatility share is capped at 50% of that allocation per asset; unused weight remains cash. No leverage.
- Each leg has a fixed 12% initial stop. Gaps fill at worse hourly opens. Otherwise an intrabar stop fills at the stop. Stopped legs remain cash until the next monthly rebalance. Maximum four simultaneous legs and no duplicate symbol overlap.
- Normal cost per leg and side is 0.095% fee plus 0.02% adverse slippage. Stress doubles both. Equity and drawdown are marked hourly.
- Parameters are fixed before any result is read and will not be tuned on revealed periods.

## Chronological protocol and gate

Use 2021–2022 as an initial development screen and 2023 through September 2026 as later chronological validation, reported separately by calendar block. Reject unless both development years are positive normally and validation has at least 60 completed leg trades, PF >=1.25 normally and >=1.10 under doubled costs, every validation block positive normally, at least three of four positive under stress, combined stressed validation positive, normal validation drawdown <=15%, and no single validation block supplies more than 60% of summed positive block profit.

Even a historical pass is not a robust candidate. It must then record at least 30 new forward PAPER leg trades under unchanged rules and remain positive after costs. No Render, deployed branch, paused bot or real account changes are authorized.
