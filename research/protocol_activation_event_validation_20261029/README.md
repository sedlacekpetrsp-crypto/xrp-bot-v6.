# XRP_PROTOCOL_ACTIVATION_EVENT_V1 — completed validation

Decision: **NEPROŠEL**. The fixed protocol, source feasibility, code and gates were stored in GitHub commit `164ddea10785c33b81da1404f5dc7d4878a0d865` before any price archive was downloaded or performance calculated. No threshold or rule changed after results.

This was a distinct event hypothesis: buy XRP spot only after an official XRPL mainnet amendment activation, without any price, flow, volume, attention or network-metric filter. The official `XRPLF/xrpl-dev-portal` snapshot has 105 records, 94 fully dated records and 61 unique entry dates from 2016–2026. The 2020–September 2026 price window contains 43 unique entry dates. Snapshot raw SHA256 is `1fe133244756ef3fcfb4db639a27f2edcce21956682898a8d5cbbaf12036b1eb`; exact URL, byte count and all 81 Binance archive URLs/SHA256 hashes are in `results.json`.

Actual Binance Vision XRPUSDT daily archives contain 2,465 consecutive UTC candles from 2020-01-01 through 2026-09-30, with zero duplicates and zero gaps. No price or event was imputed. Events sharing an activation date were grouped. Entry was the first 00:00 UTC open strictly after the latest activation timestamp in the group. Current amendment status and later metadata did not select signals.

All 217 repository tests passed, including six new activation timing, duplicate, missing-date, stop-first, gap-stop, sizing, cost-stress, non-overlap and future-prefix tests. The independent audit passed 1,320 source-hash, event membership/timing, chronology, price, fill, fee, slippage, risk, cap, non-overlap, equity and report checks without importing strategy code. Tests validate mechanics, not profitability.

| Annual OOS fold | Trades | Base net P&L | Base PF | Double-cost net P&L | Stress PF |
|---|---:|---:|---:|---:|---:|
| 2022 | 2 | -$65.34 | 0.000 | -$67.13 | 0.000 |
| 2023 | 3 | -$14.27 | 0.682 | -$16.94 | 0.637 |
| 2024 | 6 | +$16.32 | 1.100 | +$9.30 | 1.056 |
| 2025 | 6 | -$91.81 | 0.547 | -$97.71 | 0.527 |
| 2026 through September | 6 | -$122.39 | 0.398 | -$128.93 | 0.380 |
| Aggregate reset folds | 23 | -$277.49 | 0.592 | -$301.42 | 0.566 |

Aggregate expectancy is -$12.06 per trade base and -$13.11 stressed. Continuous 2022–September 2026 has 24 trades, -$257.97, PF 0.617 and 3.85% conservative drawdown; stress is -$282.45, PF 0.590 and 4.07% drawdown. Continuous and annual-fold trades are repeated evidence and must not be added. Their counts differ because each annual fold starts flat while the continuous simulator can skip a new-year event when a prior-year position remains open.

The candidate fails sample (23 versus frozen 75), net result, expectancy, PF, annual stability, final-year and concentration gates at both cost levels. Only 2024 is positive. The 2020–2021 control has eight trades and is positive, but cannot override later OOS losses and was not used for selection. No forward PAPER evidence exists. Daily OHLC is not tick execution; stop-first ambiguity, adverse slippage, gap-stop and candle-low drawdown are conservative approximations. Amendment activations are also anticipated through validator voting, so activation timestamps need not be market surprises.

Reproduce from repository root:

```sh
python -m unittest discover -s tests -v
python -m research.run_protocol_activation_event /tmp/protocol-activation-cache research/protocol_activation_event_validation_20261029
python -m research.audit_protocol_activation_event /tmp/protocol-activation-cache research/protocol_activation_event_validation_20261029
```

Full ledgers are in `trades.json.gz`; metrics, gates and provenance are in `results.json`; independent checks are in `audit.json`. No production, main, `v8-fly-layer-test`, Render, infrastructure, paused strategy or LIVE setting was touched.

Next concrete step: do not retune this sparse event family. Research a new mechanism with naturally higher causal event frequency and a fresh preregistered period; retain the 75-trade and independent-forward requirements.
