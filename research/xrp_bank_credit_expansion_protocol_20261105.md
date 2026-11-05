# XRP_BANK_CREDIT_EXPANSION_V1 — frozen protocol

Preregistered 2026-11-05 before inspecting any historical `BUSLOANS` value or XRP return for this hypothesis. Offline PAPER only.

## Hypothesis and fixed signal

Expansion in U.S. commercial-and-industrial bank credit is a distinct credit-quantity mechanism that can precede greater speculative risk capacity. Use only the Federal Reserve Bank of St. Louis FRED `BUSLOANS` weekly seasonally-adjusted series. At observation `t`, information is eligible only after two later actual published observations. Signal when the eligible value is at least 1.5% above the value 13 actual observations earlier. Missing FRED values are excluded, never filled. The signal contains no crypto price, flow, volume, relative-strength, volatility, derivatives, on-chain or calendar input.

## Sources and frozen sample

- FRED CSV: `https://fred.stlouisfed.org/graph/fredgraph.csv?id=BUSLOANS&cosd=2020-01-01&coed=2026-10-01`.
- Binance Vision public data API: XRPUSDT spot daily OHLC, 2020-01-01 through 2026-09-30 inclusive.
- Retain exact URLs, response byte counts, row counts and SHA256. Explicit missing values and market gaps are reported and not imputed.
- 2020–2021 is a control. Annual-reset OOS folds are 2022, 2023, 2024, 2025 and 2026 through September. A 2022–September 2026 continuous run is descriptive only.

## Execution fixed before evaluation

Map each eligible weekly observation date to an XRP candle only when that exact UTC calendar date exists. Enter long at the next consecutive daily open. ATR(14) uses only completed candles through the signal candle. Stop is 2 ATR below the adverse-slippage entry; target is 3R; maximum hold is seven daily bars. A gap through the stop fills at the worse open; ambiguous same-bar stop/target fills stop first. A data gap exits at the prior close. An open position at a fold boundary liquidates at the last actual close. Entry and exit each pay 0.095% fee and 0.020% adverse slippage; stress doubles both. Risk is 0.5% of current equity with a 20% notional cap, no leverage, one position, and no overlap.

## Frozen gates

Historical acceptance requires all of: at least 75 annual OOS trades; positive net and expectancy at base and stress costs; base PF >1.15 and stress PF >1.02; at least four of five annual folds positive at both costs including 2026; continuous base/stress drawdown <=10%; largest positive month <=25% of total positive-month profit; and independent audit success. `PROŠEL` additionally requires a new prospective PAPER window of at least 30 calendar days and at least 100 total qualifying trades without changing rules. Historical success alone remains `TEST NEDOKONČEN`. Any failed historical gate is `NEPROŠEL`. No threshold, lag, direction, hold, cost, fold or gate may be retuned after results.

Known limitation: FRED can revise history; the retained response hash identifies the evaluated file, not its original release vintage. The two-observation lag is a conservative anti-lookahead rule, not proof of point-in-time vintage reconstruction.
