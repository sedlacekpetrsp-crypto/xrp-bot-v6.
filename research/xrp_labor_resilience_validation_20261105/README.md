# XRP_LABOR_RESILIENCE_V1 validation

Verdict: **NEPROŠEL**. Offline PAPER only; not approved for deployment.

The hypothesis and fixed gates were remotely preregistered before data retrieval. Two pre-performance corrections were separately committed: normalization of synthetic-test compatibility aliases and alignment of the audit's local cache filename. Neither changed source URLs, signal rules, timing, execution or gates.

## Sources and integrity

- FRED `ICSA`: 404 ordered weekly observations from 2019-01-05 through 2026-09-26, no explicit missing value; response SHA256 `8af1f61b15b464703a3fb41851d1b6ee097cc7fd4215ea902d3c8ffc051998f6`.
- Binance XRPUSDT daily: 2,465 consecutive candles from 2020-01-01 through 2026-09-30, no detected gap. All three response SHA256 values and exact URLs are in `results.json`.
- No claims observation, weekend, holiday or price was filled. A two-actual-observation lag, exact-date mapping and next-consecutive-open entry were enforced. Revised FRED history cannot reconstruct original release vintages.

## Frozen OOS result

The five annual-reset OOS folds contain 96 trades and lose USD 283.86, PF 0.8037 and USD -2.96 expectancy at base costs. Doubled costs lose USD 396.92, PF 0.7380 and USD -4.13 expectancy. Only 2023 and incomplete 2026 are positive; 2022, 2024 and 2025 lose. Continuous OOS loses USD 318.56 base and USD 427.80 stressed with conservative marked drawdown 4.73%/5.78%.

Sample, final-year and drawdown gates pass. Net, expectancy, PF, four-year stability and concentration gates fail at base and stress. The independent audit passes 7,622 checks, and all 317 repository tests pass. These establish mechanics, not profitability. Do not change the median, four-week comparison, lag, direction or holding period after observing this result. Close this labor-resilience design.

Evidence: `results.json`, `trades.json.gz`, `audit.json` and `unit_tests.txt` in this directory. Next work should begin with source-coverage feasibility for a genuinely different observable, not another labor/macro threshold.
