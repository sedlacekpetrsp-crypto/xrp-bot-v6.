# XRP_RELATIVE_STRENGTH_V1 — completed exploratory validation

Decision: **NEPROŠEL**. Historical net profit is not sufficient evidence for promotion.

The original fixed protocol was saved in commit `4ce6080187c3af4d590c8192e0131f790d63a229` before evaluation. The data-gap amendment was separately committed before any performance results. No parameters were selected or adjusted based on returns.

171 real Binance monthly archives, Jan 2022–Sep 2026: 41,615 actual hourly candles per market (XRPUSDT, BTCUSDT, ETHUSDT), 124,845 total. All three archives omit March 24, 2023 13:00 UTC. The API query `https://data-api.binance.vision/api/v3/klines?symbol=XRPUSDT&interval=1h&startTime=1679662800000&endTime=1679666399999&limit=1` independently returned `[]`. No bars were fabricated; signals require a complete preceding 720-hour history. Exact source URLs, SHA256 hashes and gap timestamps are retained in results.json. Hashes identify downloaded bytes, not independently verified publisher signatures.

21 research tests pass, including 10 new relative-strength tests. An independent arithmetic audit (no strategy import) also passes: chronology, no overlapping positions, daily entry timing, notional/risk limits, fees/slippage and equity reconciliation. Unit tests do not prove profitability.

| Period | Trades | Net return | PF | Double-cost return | Stress PF |
|---|---:|---:|---:|---:|---:|
| 2022 control | 10 | -2.281% | 0.219 | -2.669% | 0.162 |
| 2023 OOS | 13 | 0.955% | 1.225 | 0.505% | 1.110 |
| 2024 OOS | 23 | 6.540% | 1.909 | 5.714% | 1.746 |
| 2025 OOS | 13 | 2.096% | 1.564 | 1.595% | 1.397 |
| 2026 OOS | 11 | -3.056% | 0.079 | -3.442% | 0.059 |

Annual OOS folds reset $10,000 equity and sum to $653.46 net, PF 1.354 (stress $437.17, PF 1.219). These summed fold profits are NOT a compounded portfolio return. Continuous Jan 2023–Sep 2026 OOS: +6.456% net, PF 1.337, conservative drawdown 6.069%; stress +4.227%, PF 1.206, drawdown 6.397%. Only 60 trades, below the frozen minimum 100. The final 2026 fold loses at both costs. November 2024 supplies more than half the summed OOS profit, failing concentration. Three of four annual OOS folds are positive but this does not override failed gates. The 2022 control also loses. No selection of profitable years or post-hoc changes to thresholds.

The fixed 20%-initial-notional XRP buy-and-hold comparison earns $6,779.39 over continuous OOS at base costs, versus strategy $645.56; it is descriptive and has different exposure/risk. This comparison excludes rebalancing, interest on unused cash, custody/platform risk and taxes. The strategy is long-only spot, so no derivatives funding/borrow fees apply. Fees 9.5 bps and slippage 2 bps per side; stress doubles both. Stop-distance risk excludes costs and can be exceeded by gaps. Candle-low drawdown is conservative on exit candles and not tick-exact.

The separate continuous run repeats the same observations as annual folds: do not add their trades as independent evidence. All history is exploratory, especially previously inspected 2025–2026 dates. No forward PAPER evidence exists. Candidate is rejected for promotion; do not tune it to the failing 2026 period. A next hypothesis must have a distinct mechanism and a newly frozen protocol; a positive historical subset is not grounds to modify production.

Reproduce from repo root:

```sh
python -m unittest discover -s tests -v
python -m research.run_relative_strength /tmp/crypto-archives research/relative_strength_validation_20261024
python -m research.audit_relative_strength research/relative_strength_validation_20261024
```

Full trade ledgers are in trades.json.gz; metrics and provenance in results.json; independent checks in audit.json. Changes are confined to research and tests on `autocorr-regime-research-20261024`. No production bots, Render settings, main branch or LIVE trading were changed.
