# XRP_TRANSFER_UTILIZATION_SHARE_V1 — frozen protocol (2026-10-30)

Status: **PREREGISTERED; PERFORMANCE NOT YET EVALUATED.** Offline research only.

## Distinct hypothesis

The fraction `TxTfrCnt / TxCnt` measures how much XRPL transaction activity contains value transfers rather than non-transfer ledger operations. A top-quintile transfer-utilization share is hypothesized to identify periods of genuine settlement demand and positive subsequent XRP spot expectancy. This compositional, scale-invariant mechanism is distinct from rejected `XRP_LEDGER_ACTIVITY_BREADTH_V1`, which jointly screened absolute active-address and transaction-count levels; it does not use active addresses or any absolute activity threshold. It is also not a price, flow, fee, holder-growth, macro, derivatives, calendar, developer, cadence or protocol-event variant.

## Fixed causal signal and source

Use direct CoinMetrics Community XRP daily `TxCnt` and `TxTfrCnt`. Retain URL, raw payload bytes and SHA256. Require strictly consecutive exact UTC days, `TxCnt>0`, `TxTfrCnt>=0`, and finite values. Do not fill or interpolate. For each day D, compute share `TxTfrCnt/TxCnt`. Compare it with the nearest-rank 80th percentile of the 180 shares from D-180 through D-1, excluding D. Signal when current share is greater than or equal to that threshold. Metric day D is conservatively treated as available after D+1; enter the XRPUSDT daily open at D+2. No price or raw-count filter selects signals.

## Fixed execution

Long XRP spot only, zero leverage, one position. ATR14 from the preceding fully closed daily candles. Stop 2 ATR below the adverse entry fill, target 3R, maximum 10 candles including entry. Stop wins ambiguous candles; gaps through stop fill at the worse open. Fee 9.5 bps and adverse slippage 2 bps per side; stress doubles both. Risk 0.5% of current equity at stop, capped at 20% notional. Signals during an open position are skipped. A data gap exits at the last actual close before it; no price is invented.

## Locked evaluation and acceptance

Use actual Binance Vision XRPUSDT 1d archives January 2020–September 2026. 2020–2021 is control; reset annual OOS folds 2022–2026 through September plus a separate continuous OOS diagnostic. Preserve all hashes, gaps, ledgers and independent audit. No tuning after results.

Historical gates: >=120 aggregate OOS trades; positive base net/expectancy with PF>1.20; positive double-cost net/expectancy with PF>1.05; >=4/5 OOS years positive at both costs including 2026; continuous base/stress drawdown <=10%; no month >25% of positive monthly profit; independent audit passes hashes, exact nearest-rank share arithmetic and lag, chronology, fills, costs, sizing, non-overlap, equity and reports.

Even a full historical pass remains `TEST NEDOKONČEN` until >=30 future calendar days and >=100 newly timestamped forward PAPER trades have positive stressed expectancy. Historical results or code tests never mean `PROŠEL`. A failed completed gate means `NEPROŠEL`; do not change lookback or percentile on these dates.

Next action: commit this protocol, implementation and mechanics tests to the isolated research branch before performance evaluation; then run unchanged multi-year validation and independent audit.
