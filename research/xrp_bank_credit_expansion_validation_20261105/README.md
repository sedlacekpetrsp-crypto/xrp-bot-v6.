# XRP_BANK_CREDIT_EXPANSION_V1 validation

Verdict: **NEPROŠEL**. Offline PAPER only; not approved for deployment.

The frozen protocol was remotely preregistered before source retrieval. A fixture-only correction was committed before data retrieval. The first generated output was invalidated because its drawdown curve omitted open-position mark-to-market lows; an accounting-only correction was documented and remotely committed before the complete rerun. Signal, source, thresholds, lag, execution, costs, folds and gates were unchanged.

## Reproducible sources

- FRED `BUSLOANS`: 81 ordered weekly observations, no explicit missing value, response SHA256 `4e9a916ba8001f0c6a893501012495c1aaa899dd67ce011f6df0294b393bb9f4`.
- Binance XRPUSDT daily: 2,465 consecutive candles from 2020-01-01 through 2026-09-30, no detected gap. The three response SHA256 values are recorded in `results.json`.
- No credit observation, weekend, holiday or market price was filled. The two-actual-observation lag and next-consecutive-open rule prevent same-observation use, but revised FRED history cannot reconstruct original release vintages.

## Frozen OOS result

Annual-reset 2022–September 2026 contains only 22 trades. Base costs lose USD 260.26, PF 0.3348 and expectancy USD -11.83 per trade. Doubled costs lose USD 286.08, PF 0.2984 and expectancy USD -13.00. 2022, 2023 and final 2026 lose at both costs; 2024 and 2025 have no trades. The separate continuous path loses USD 259.62 base and USD 285.04 stressed with conservative marked drawdown 3.41%/3.63%.

The sample, net, expectancy, PF, annual stability, final-year and concentration gates fail. The independent audit passes 1,504 checks, and the complete repository suite passes 310 tests. These validate mechanics only. Do not lower the 1.5% growth threshold, shorten the 13-observation horizon, alter the lag or select the profitable 2020–2021 control. Close this bank-credit expansion design.

Evidence: `results.json`, `trades.json.gz`, `audit.json`, and `unit_tests.txt` in this directory. Next work should first establish reproducible coverage for a genuinely different observable rather than retune this credit-quantity family.
