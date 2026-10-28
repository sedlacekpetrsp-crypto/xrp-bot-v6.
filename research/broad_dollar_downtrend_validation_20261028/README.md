# XRP_BROAD_DOLLAR_DOWNTREND_V1 — completed validation

Decision: **NEPROŠEL**. The external fiat-macro hypothesis, execution rules and
gates were committed before performance evaluation.

The test used the direct FRED `DTWEXBGS` CSV and real Binance Vision XRPUSDT
daily spot archives from January 2020 through September 2026. Each FRED value
became eligible only on the date of the second subsequent valid observation;
the trade entered at the next XRP daily open. Weekends, holidays and 73 explicit
FRED missing-value rows were not filled. The dataset retained 1,688 valid macro
observations and 2,465 consecutive XRP days. Exact URLs, byte counts and local
SHA256 fingerprints for all 82 payloads are in `results.json`.

The five annual OOS folds produced 35 trades: -$284.45 net, PF 0.654 and -$8.13
expectancy at base costs. Doubled fees/slippage lost $321.63, PF 0.620 and
-$9.19 expectancy. The descriptive continuous path lost $268.23 base and
$304.45 stressed, with 3.92%/4.16% drawdown. Only 2023 and 2025 were positive;
2022, 2024 and the final 2026 fold lost at both cost levels.

Every frozen profitability, sample, stability, final-year and concentration
gate failed; only drawdown passed. Do not invert the signal, select the two
profitable years, shorten the dollar lookback or tune the threshold after this
result.

All 161 repository tests passed. The independent audit performed 1,394 checks
of release lag, macro threshold, next-open timing, non-overlap, sizing, fees,
slippage and P/L without importing the strategy module. Tests establish
implementation consistency, not future profitability.

```sh
python -m unittest discover -s tests -v
python -m research.run_broad_dollar_downtrend /tmp/dollar-cache research/broad_dollar_downtrend_validation_20261028
python -m research.audit_broad_dollar_downtrend research/broad_dollar_downtrend_validation_20261028
```

Next step: reject this macro-dollar rule without retuning and move to a distinct
mechanism or genuinely independent future evidence. It is not promoted to
forward PAPER. Production, Render, deployed branches, paused strategies and
LIVE remain untouched.
