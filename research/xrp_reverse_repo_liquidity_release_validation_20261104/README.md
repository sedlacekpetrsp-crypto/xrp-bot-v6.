# XRP_REVERSE_REPO_LIQUIDITY_RELEASE_V1 — final validation

Final decision on 2026-11-04: **NEPROSEL**. Offline research only; no forward
PAPER promotion and no production, Render or LIVE change.

## Frozen mechanism and provenance

The remotely preregistered strategy treated a rapid fall in the Federal
Reserve's overnight reverse-repo balance as a release of dollar liquidity. A
signal required the lagged FRED `RRPONTSYD` value to be at least 10% below its
level 20 actual observations earlier, with the earlier level at least USD 100
billion. Each observation was delayed to the date of the second subsequent
actual FRED observation. Entry was the next XRP calendar-day open; no crypto
series entered the signal.

The direct FRED CSV contains 1,761 dated rows, of which 1,686 carry valid values
from 2020-01-02 through 2026-10-01. Seventy-five explicit missing-value rows
were excluded and no weekend, holiday or missing value was filled. Three direct
Binance Vision API responses contain 2,465 consecutive daily XRPUSDT candles
from 2020-01-01 through 2026-09-30, with no duplicate or missing price date.
`results.json` retains every URL, byte count, row count, exclusion and SHA256
payload fingerprint. Hashes identify the evaluated downloads, not independently
signed publisher files; FRED can revise history.

## Locked OOS result

The five annual-reset OOS folds contain 85 non-overlapping base-cost trades and
earn **USD 55.33**, PF **1.0448**, expectancy **USD 0.65**. This fails the frozen
PF >1.15 gate. When fee and slippage are doubled, the same 85-fold aggregate
loses **USD 35.31**, PF **0.9725**, expectancy **-USD 0.42**. Base fees were USD
75.84 and modeled slippage USD 15.97; stress fees were USD 151.45 and slippage
USD 31.88.

Annual base P/L for 2022–2026 is USD 152.21, -30.81, 69.88, -85.21 and -50.74.
Only 2022 and 2024 are positive; the same two years alone remain positive at
doubled costs. The continuous OOS path earns USD 53.45/PF 1.0427 base but loses
USD 37.36/PF 0.9712 under stress; drawdown is 3.15%/3.76%. The 2020–2021
control loses at both costs. November 2024 supplies 45.56% of all positive-month
profit, above the frozen 25% concentration limit.

Only sample size, base net/expectancy and drawdown pass. Base PF, every stressed
profit gate, annual stability, final-2026 and concentration fail. No independent
forward PAPER evidence exists. Reject without changing the RRP threshold,
minimum balance, lag, lookback, direction or exit.

## Verification and limitations

- `results.json`: complete metrics, gates, quality diagnostics and source manifest.
- `trades.json.gz`: every control, annual and continuous ledger at both costs.
- `audit.json`: independent reconstruction passed 5,192 checks over 344 recorded
  trade instances, with zero failures.
- `unit_tests.txt`: all 295 repository tests passed, including seven new timing,
  threshold, gap-stop, gap suppression, cost and sizing tests.

Reproduce from repository root:

```bash
python -m research.run_xrp_reverse_repo_liquidity_release CACHE_DIR research/xrp_reverse_repo_liquidity_release_validation_20261104
python -m research.audit_xrp_reverse_repo_liquidity_release research/xrp_reverse_repo_liquidity_release_validation_20261104 CACHE_DIR
python -m unittest discover -s tests -v
```

RRP declines can reflect Treasury issuance and money-market allocation rather
than cash entering crypto. Daily OHLC cannot reconstruct tick ordering, so the
frozen conservative stop-first and gap rules apply. Previously inspected dates
remain exploratory and successful mechanics do not establish profitability.

