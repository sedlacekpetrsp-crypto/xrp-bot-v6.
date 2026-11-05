# XRP_POLICY_UNCERTAINTY_EASING_V1 validation

Verdict: **NEPROŠEL**. Offline PAPER only; not approved for deployment.

The source, signal, execution and gates were remotely preregistered before source retrieval. Direct FRED supplied 2,831 ordered `USEPUINDXD` observations with no explicit missing value; response SHA256 is `ba0f2bb695ee41ebd7ab70269b17273fc5d9a15f4b408a72b3fe53f6ede8c5e8`. Three retained Binance responses supplied 2,465 consecutive XRPUSDT daily candles through 2026-09-30 with no detected price gap. Exact URLs, bytes and all SHA256 values are in `results.json`. No index value, weekend, holiday or price was filled. Eighty-one eligible source dates after the XRP cutoff were reported rather than mapped.

The five annual-reset OOS folds contain 175 trades and lose USD 619.91, PF 0.7689 and USD -3.54 expectancy at base costs. Doubled costs lose USD 813.18, PF 0.7089 and USD -4.65 expectancy. Only 2024 is positive; 2022, 2023, 2025 and final 2026 lose. Continuous OOS loses USD 567.75 base and USD 750.03 stressed; conservative marked drawdown is 8.58%/10.27%.

Only sample size passes. Net, expectancy, PF, annual stability, final-year, stress drawdown and concentration gates fail. The independent audit passes 11,736 checks and all 324 repository tests pass. Do not invert the signal or alter the 90-observation median, five-observation trend, lag, direction or hold after this result. Close this policy-uncertainty easing design.

Evidence: `results.json`, `trades.json.gz`, `audit.json`, `unit_tests.txt`. Next work must first establish a genuinely different reproducible source rather than mine another external macro threshold.
