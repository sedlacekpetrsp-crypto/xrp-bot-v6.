# XRP_LEDGER_CADENCE_HEALTH_V1 — source feasibility (2026-10-29)

Performance was not evaluated before this record.

- Direct source: `https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=xrp&metrics=BlkCnt&frequency=1d&page_size=10000`.
- Raw payload SHA256: `d5037dc63ad7a8e5d20b7048f71918bacb665f9040885f480222aebbb2f98087`; 368,408 bytes.
- Full response: 5,049 daily rows from 2013-01-01 through 2026-10-28.
- Frozen market window 2020-01-01 through 2026-09-30: 2,465 consecutive unique dates, zero gaps, first value 22,246 and last value 22,277 ledgers/day.
- Window range: 20,802 to 23,595 ledgers/day. There are 51 days below the fixed 21,600 median-regime threshold and zero below the separately fixed 20,000 recent-minimum threshold.
- These source-distribution facts were checked only to validate units, coverage and the engineering meaning of the thresholds; no XRP price or strategy return was inspected.
- CoinMetrics Community is a third-party public metric source. The local hash identifies exact bytes but is not a publisher signature.

Feasibility conclusion: the direct metric has complete exact-date coverage for control and all locked OOS periods. Proceed without changing the source, thresholds or rules. This conclusion says nothing about profitability.
