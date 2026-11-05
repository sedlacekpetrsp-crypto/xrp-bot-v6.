# XRP_YIELD_CURVE_STEEPENING_V1 — final validation

Final decision on 2026-11-05: **NEPROSEL**. Offline research only; no forward
PAPER promotion and no production, Render or LIVE change.

## Frozen mechanism and provenance

The remotely preregistered strategy treated a rise of at least 0.25 percentage
point in the U.S. Treasury 10-year minus 2-year spread across 20 actual FRED
observations as a growth/credit-cycle signal. Each value was delayed until the
date of the second subsequent actual FRED observation; entry occurred at the
next XRP calendar-day open. No crypto-derived value entered the signal.

The direct FRED `T10Y2Y` response contains 1,761 dated rows, of which 1,689 have
valid values from 2020-01-02 through 2026-10-01. Seventy-two explicit missing
rows were excluded; weekends, holidays and missing values were not filled.
Three direct Binance Vision responses contain 2,465 consecutive XRPUSDT daily
candles from 2020-01-01 through 2026-09-30, with no duplicate or missing price
date. `results.json` retains exact URLs, bytes, rows, exclusions and SHA256
payload fingerprints. FRED can revise history, so its hash identifies the
evaluated download rather than an original publication vintage.

## Locked OOS result

Five annual-reset OOS folds contain only **27 non-overlapping trades**, far
below the frozen minimum of 75. They earn **USD 339.56**, PF **2.2020** and USD
12.58 expectancy at base costs. Doubled costs remain positive at **USD 309.70**,
PF **2.0489** and USD 11.47 expectancy. Base fees were USD 24.96 and modeled
slippage USD 5.26; stressed fees were USD 49.91 and slippage USD 10.51.

Annual base P/L for 2022–2026 is -USD 72.69, USD 306.57, USD 35.55, USD 70.14
and USD 0.00. Stress preserves the same pattern. Only three of five folds are
positive; 2022 loses and 2026 produces no trade, which is not a positive year.
The continuous OOS diagnostic earns USD 349.12/PF 2.3709 base and USD
318.70/PF 2.1999 stressed, with 1.21%/1.27% drawdown. The 2020–2021 control is
positive but contains only eight trades and is not OOS evidence. March 2023
supplies 39.78% of positive-month profit, above the frozen 25% limit.

Profit, stress and drawdown gates pass, but sample, annual stability, final-year
and concentration gates fail. No independent forward PAPER evidence exists.
Reject without lowering the threshold or sample requirement, selecting
2023–2025, treating zero exposure as a profitable year, or changing the lag,
lookback, direction or exit.

## Verification and limitations

- `results.json`: complete metrics, gates, data diagnostics and source manifest.
- `trades.json.gz`: control, annual and continuous ledgers at both cost levels.
- `audit.json`: independent reconstruction passed 1,768 checks over 124 recorded
  trade instances, with zero failures.
- `unit_tests.txt`: all 302 repository tests passed, including seven new signal,
  timing, gap-stop, gap suppression, cost and sizing tests.

Reproduce from repository root:

```bash
python -m research.run_xrp_yield_curve_steepening CACHE_DIR research/xrp_yield_curve_steepening_validation_20261105
python -m research.audit_xrp_yield_curve_steepening research/xrp_yield_curve_steepening_validation_20261105 CACHE_DIR
python -m unittest discover -s tests -v
```

Curve steepening can arise from inflation or term-premium changes rather than
improving risk appetite. Daily OHLC cannot reconstruct tick ordering, so the
frozen conservative stop-first and gap rules apply. Positive historical results
with 27 trades do not establish robustness or future profitability.

