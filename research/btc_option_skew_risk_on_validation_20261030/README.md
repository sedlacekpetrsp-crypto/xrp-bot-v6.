# BTC_OPTION_SKEW_RISK_ON_XRP_V1 — completed validation

Decision: **NEPROŠEL**. The profitable aggregate does not override failed frozen sample, stability, final-year and concentration gates. Do not tune or invert the skew rule and do not start forward PAPER.

The protocol, implementation, downloader, audit and tests were saved remotely in commit `c115dfb57052449f7b5bf8c7af05dd03c407881a` before XRP performance evaluation. This hypothesis used the call-versus-put shape of BTC option-implied tail pricing, not the already rejected absolute DVOL-minus-realized variance premium.

## Actual sources and coverage

The downloader queried every Friday 12:00–13:00 UTC from 2021-01-01 through 2026-09-25 through Deribit's official public History API. An interval reporting more results was recursively bisected until each used response had `has_more=false`; trade IDs were deduplicated. The manifest contains 458 Deribit responses totaling 67,207,584 bytes plus three Binance XRP daily responses. Every exact URL, byte count and locally calculated SHA256 is in `results.json`. The used complete Deribit partitions contain 199,624 trade records. Local hashes are provenance fingerprints, not publisher signatures.

Of 300 sampled weeks, 233 had the frozen minimum of five eligible call and put trades and amount >=1 on each side after the 14–60 day maturity and 0.15–0.35 absolute-delta filters. Eighty-four weeks had positive trade-print skew. Missing or thin sides were not imputed. The metric is an unweighted median of reported trade IV and is not a synchronized, executable quote surface. Black-Scholes delta uses a fixed zero-rate approximation.

Binance XRPUSDT contains 2,465 consecutive daily candles from 2020-01-01 through 2026-09-30 with no gaps or fabricated prices. All 247 repository research tests passed, including seven new causal/skew/execution tests. The independent implementation-free audit passed 5,912 checks over 302 ledger records and reconstructed source hashes, recursive completeness flags, metrics, fills, costs, stops, position limits and reports.

## Frozen-gate results

| Annual OOS folds, reset capital | Trades | Net P/L | PF | Expectancy | Fees | Slippage cost |
|---|---:|---:|---:|---:|---:|---:|
| Base costs | 67 | +$456.89 | 1.443 | +$6.82 | $61.94 | $13.04 |
| Double costs | 67 | +$382.48 | 1.357 | +$5.71 | $123.74 | $26.05 |

| Year | Positive-skew weeks | Base net P/L | Double-cost net P/L |
|---|---:|---:|---:|
| 2022 | 0 | -$50.70 | -$51.39 |
| 2023 | 27 | +$140.43 | +$110.76 |
| 2024 | 22 | +$304.42 | +$278.30 |
| 2025 | 17 | +$90.26 | +$73.36 |
| 2026 through September | 1 | -$27.52 | -$28.55 |

The negative 2022 fold contains one boundary-position liquidation even though no 2022 Friday had positive skew; its entry signal originated on the final Friday of 2021 and entered Monday 2022-01-03 using only prior information. Annual folds start flat but use causally available preceding observations. This does not change the rejection.

The separate continuous OOS diagnostic has 68 trades and earns +$501.09, PF 1.477, drawdown 2.89%; stress earns +$423.86, PF 1.390, drawdown 3.16%. It reuses the same observations and cannot be added to the annual-fold sample. Aggregate history passes net, expectancy, PF, stress and drawdown gates, but has only 67 trades versus the frozen 100 minimum; only 3/5 annual folds are profitable; final 2026 loses; and 2024 supplies 56.89% of positive annual profit. No forward PAPER evidence exists.

The sharp absence of positive skew in 2022 and near-absence in 2026 is itself a regime-instability warning. Selecting only 2023–2025, weakening `risk_reversal > 0`, widening delta/maturity bands or lowering the sample gate after seeing this would be invalid post-hoc optimization.

Reproduce from repository root:

```sh
python -m unittest discover -s tests -v
python -m research.run_btc_option_skew_risk_on /tmp/btc-option-skew-cache research/btc_option_skew_risk_on_validation_20261030
python -m research.audit_btc_option_skew_risk_on /tmp/btc-option-skew-cache research/btc_option_skew_risk_on_validation_20261030
```

Next concrete step: leave this options family closed. Verify source coverage for a genuinely different BTC network-security mechanism using direct daily hashrate and difficulty observations, and preregister a miner-stress hypothesis only if multi-year data are consecutive and independently hashable. Do not combine it post hoc with the profitable skew years.

No production bot, main, `v8-fly-layer-test`, Render, infrastructure, paused strategy or LIVE trading was changed.
