# XRP_PROTOCOL_ACTIVATION_EVENT_V1 — frozen protocol (2026-10-29)

Status: **PREREGISTERED; PERFORMANCE NOT YET EVALUATED.** This is offline research only and is not evidence of profitability.

## Distinct hypothesis

A mainnet amendment activation is an externally timestamped change to XRPL capabilities and rules. The fixed hypothesis is that completed activations create a short adoption/repricing window with positive XRP spot expectancy. This is an event study, not a variant of rejected price trend, reversal, volume/flow, relative strength, attention, derivatives, macro, developer-count, or ledger-cadence rules. No price or activity condition selects events.

## Immutable source and event construction

Use the official `XRPLF/xrpl-dev-portal` amendment snapshot at `@theme/data/amendments-snapshot.json`. Retain its raw bytes, URL and local SHA256. An eligible event must have non-null `date`, `ledger_index`, and `tx_hash`. Group amendments sharing the same UTC activation date into one event. The entry is the first 00:00 UTC Binance daily open strictly after the latest activation timestamp in that group; this guarantees the activation was already public. Current snapshot status, name, version, retirement and later metadata never condition entry. Duplicate IDs or conflicting records are fatal. No missing event or price is invented.

Source feasibility before performance: snapshot fetched 2026-10-29, SHA256 `1fe133244756ef3fcfb4db639a27f2edcce21956682898a8d5cbbaf12036b1eb`, 105 records, 94 dated from 2016-05-19 through 2026-09-11. The prospective price window has 43 distinct activation dates in 2020–2026. This makes the frozen 75-OOS-trade gate difficult or impossible; the gate will not be weakened.

## Fixed trade and execution rules

Long XRPUSDT spot only, zero leverage, one position maximum. At every eligible entry open: ATR14 from the 14 fully closed preceding daily candles; buy with adverse 2 bps entry slippage; stop 2 ATR below fill; target 3R; maximum 14 daily candles including entry candle. If stop and target are both possible, stop wins. A gap through stop fills at the worse open. Exit has adverse 2 bps slippage. Fee is 9.5 bps per side. Stress doubles both fee and slippage. Risk is 0.5% of current equity at the stop, capped at 20% notional. A signal during an open position is skipped, so positions never overlap. A price gap forces liquidation at the last observed close before the gap; no synthetic candle.

## Chronology and frozen acceptance gates

Download actual Binance Vision XRPUSDT 1d monthly archives, January 2020–September 2026, preserving each URL, byte count and SHA256. Require valid ordered OHLC and record duplicates/gaps. Use 2020–2021 as control and annual OOS folds 2022, 2023, 2024, 2025 and January–September 2026, each reset to $10,000, plus a continuous 2022–2026 diagnostic. No tuning after inspection.

Historical gates: at least 75 aggregate OOS trades; base net P&L and expectancy positive with PF >1.20; double-cost net P&L and expectancy positive with PF >1.05; at least 4/5 annual OOS folds positive at both costs including 2026; continuous base and stress drawdown <=10%; no month contributes >40% of positive monthly profit; independent audit passes source hashes, event lag, chronology, prices, fills, costs, risk, cap, non-overlap, equity and report reconciliation.

Even if every historical gate passes, status remains `TEST NEDOKONČEN` until at least 30 future calendar days and 75 newly timestamped forward PAPER event trades have positive stressed expectancy. Historical success or code tests alone can never mean `PROŠEL`. Any failed completed historical gate means `NEPROŠEL`; parameters will not be retuned on these dates.

Next step: commit this protocol, implementation and mechanics tests to the isolated research branch before downloading price data or calculating performance; then run the unchanged validation and independent audit and save full results and journal entry.
