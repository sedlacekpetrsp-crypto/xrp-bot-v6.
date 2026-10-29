# XRP_FINANCIAL_CONDITIONS_EASING_V1 source feasibility (2026-10-29)

Performance was not evaluated before this note was committed.

## Selected source

- Direct URL: https://fred.stlouisfed.org/graph/fredgraph.csv?id=NFCI&cosd=2020-01-01&coed=2026-10-01
- Series: Chicago Fed National Financial Conditions Index (NFCI), weekly index.
- Retrieved payload SHA256: `25b7b4ac0f37d3b740950c2d5b943fdd07e27e0bd54898c8c9da6412d61df288`.
- 352 observations after the header, 2020-01-03 through 2026-09-25.
- Missing values, if any, remain missing; the fixed signal uses valid-observation positions and a two-subsequent-valid-observation availability lag.

## Rejected source path

The direct free FRED BAMLH0A0HYM2 export requested for 2020-01-01 through 2026-10-01 returned only 775 observations starting 2023-10-30 (retrieved SHA256 `e87cadba3d1f47577da287c0a582d4ba251b23474fc667e3d19eb533b43f1f5e`). That is insufficient for 2020–2026 control/OOS folds. It will not be backfilled, extrapolated or replaced with paid data.

Market data will use direct Binance Vision monthly XRPUSDT daily archives. The completed results will retain every archive URL, byte count, row count and freshly computed SHA256. This source check establishes availability only and does not amend the frozen protocol or provide profitability evidence.
