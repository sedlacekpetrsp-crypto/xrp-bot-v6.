# BTC_ASSET_MANAGER_ACCUMULATION_XRP_V1 — final validation

Final decision on 2026-11-04: **NEPROSEL**. Offline research only; no forward PAPER promotion or deployment.

## Frozen mechanism and sources

The remotely preregistered hypothesis tested whether institutional asset-manager accumulation in the main CME Bitcoin futures contract identified a broad crypto allocation regime that subsequently benefited XRP. The signal was the CFTC Traders in Financial Futures asset-manager net position divided by contract open interest, above the median of 52 strictly preceding reports and rising versus four reports earlier. Entry occurred only at the first Monday XRP open strictly after the report date and at least four days later, safely after the normal Friday publication.

Nine exact CFTC annual archives for 2018–2026 supplied 447 unique, strictly ordered main-contract report rows from 2018-04-10 through 2026-10-27. The fixed market code was `133741`; Micro and Nano contracts were excluded. Three direct Binance API responses supplied 2,465 consecutive XRPUSDT daily candles from 2020-01-01 through 2026-09-30. `results.json` preserves each URL, response byte count, outer ZIP SHA256, extracted member SHA256, selected row count and price-response SHA256. No report, position, open interest or price was imputed. Reports after the locked price cutoff cannot enter a historical trade.

CFTC historical annual files can be revised after the original weekly release. This source-vintage limitation is explicit and prevents treating the study as point-in-time institutional evidence. The fixed entry delay removes direct use before normal publication, but cannot reconstruct historical file vintages.

## Locked OOS result

The five annual-reset OOS folds contain 94 non-overlapping trades and lose **$501.70**, with **PF 0.7289** and **-$5.34 expectancy** at base costs. Doubled fees and slippage lose **$599.27**, with **PF 0.6860** and **-$6.38 expectancy**. Modeled base costs include $84.07 fees and $17.70 slippage; stressed costs include $167.96 fees and $35.36 slippage.

Annual base net PnL for 2022–2026 is -$309.39, -$104.91, -$3.43, -$101.98 and +$18.01. Stress PnL is -$328.18, -$140.87, -$25.84, -$115.15 and +$10.77. Only the incomplete final 2026 fold is positive. The separate continuous OOS path loses $420.78 base and $515.03 stressed, with 6.33% and 7.07% maximum drawdown. The largest positive exit month contributes 27.71% of positive monthly profit, above the frozen 25% cap. The 2020–2021 control also loses at both cost levels.

Sample, final-year sign and drawdown pass. Aggregate net, expectancy, PF, multi-year stability and concentration fail, both normally and under stress. There is no independent forward PAPER evidence. Reject without selecting 2026, changing the median or four-report condition, reclassifying CFTC participants, or tuning the holding period.

## Verification and artifacts

- `results.json`: all locked metrics, gates, data-quality checks and source manifests.
- `reports.json.gz`: all 447 parsed CFTC report rows used to construct signals.
- `trades.json.gz`: every control, annual OOS and continuous trade ledger under both cost scenarios.
- `audit.json`: independent source and ledger reconstruction passed 4,134 checks, including 456 trade checks, with zero failures.
- `unit_tests.txt`: all 282 repository tests passed.

Reproduce from repository root:

```bash
python -m research.run_btc_asset_manager_accumulation_xrp CACHE_DIR research/btc_asset_manager_accumulation_xrp_validation_20261104
python -m research.audit_btc_asset_manager_accumulation_xrp CACHE_DIR research/btc_asset_manager_accumulation_xrp_validation_20261104
python -m unittest discover -s tests -v
```

Passing mechanics do not establish future profitability. Daily OHLC cannot reconstruct tick paths; the frozen simulator applies conservative same-candle and gap rules. Next work should leave this institutional-futures positioning family closed and first verify a genuinely different source family with reproducible point-in-time observations. Production, Render, LIVE, main and `v8-fly-layer-test` remain untouched.
