# BTC_VARIANCE_RISK_PREMIUM_XRP_V1 — frozen protocol (2026-10-30)

Status: **PREREGISTERED; NO XRP PERFORMANCE EVALUATED.** Offline research only.

## Distinct hypothesis

The directly traded BTC options market can price substantially more volatility than BTC subsequently realizes. A large positive implied-minus-realized volatility premium is interpreted as expensive crash insurance / excessive option-market fear; the fixed hypothesis is that this risk premium predicts positive subsequent XRP spot expectancy. This is not a VIX level/shock rule, XRP price volatility-compression breakout, trend/reversal, cross-asset relative strength, order flow, network metric, calendar, or protocol-event variant.

## Fixed data and causal signal

Use official Deribit `public/get_volatility_index_data`, BTC, daily (`resolution=86400`) and retain every raw JSON page, URL, byte count and SHA256. Source feasibility before performance found consecutive daily DVOL OHLC from 2021-03-24 through September 2026 with backward pagination. Use actual Binance Vision BTCUSDT and XRPUSDT 1d monthly archives. No missing observation is interpolated or carried forward; a signal requires exact consecutive DVOL and BTC dates and 21 BTC closes.

For day D, compute population standard deviation of the 20 BTC close-to-close log returns ending at D, annualized by `sqrt(365)*100`. Define premium as the Deribit DVOL close for D minus that realized volatility. Signal when premium is at least 15.0 percentage points. DVOL day D and BTC close D are conservatively treated as known only at D+1 00:00 UTC; enter XRP at D+2 00:00 UTC. The extra full day prevents same-boundary publication/execution leakage. No price, return, direction, DVOL level, or later metadata otherwise filters signals.

## Fixed execution

Long XRPUSDT spot only, zero leverage, one position. ATR14 from preceding fully closed daily candles; adverse slippage 2 bps each side; fee 9.5 bps each side. Stop 2 ATR below entry fill, target 3R, maximum 10 candles including entry. Stop wins same-candle ambiguity; a gap below stop fills at the worse open. Risk 0.5% of current equity at stop, capped at 20% notional. Signals while a position is open are skipped. A data gap forces exit at the last actual close before the gap. Stress doubles fee and slippage without changing signals.

## Locked evaluation and gates

Use 2021-04-01–2021-12-31 as control; annual OOS folds 2022, 2023, 2024, 2025 and 2026 through September, reset to $10,000, plus a separate continuous OOS diagnostic. Preserve source hashes, gaps, complete trade ledgers and independent audit. No tuning after results.

Historical gates: >=100 aggregate OOS trades; base net and expectancy positive with PF>1.20; double-cost net and expectancy positive with PF>1.05; >=4/5 annual folds positive at both costs including 2026; continuous base/stress drawdown <=10%; no month >25% of positive monthly profit; independent audit passes hashes, causal volatility arithmetic/timing, chronology, fills, costs, sizing, non-overlap, equity and reports.

Even a complete historical pass remains `TEST NEDOKONČEN` until >=30 future calendar days and >=100 newly timestamped forward PAPER trades show positive stressed expectancy. Historical results or passing code tests alone never mean `PROŠEL`. A failed completed gate means `NEPROŠEL`; do not tune the 15-point premium or exits on these dates.

Next action: commit protocol, implementation and mechanics tests to the isolated GitHub research branch before downloading the complete price history or calculating performance; then run unchanged validation and independent audit.
