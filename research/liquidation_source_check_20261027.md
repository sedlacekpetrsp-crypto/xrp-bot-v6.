# Forced-liquidation archive availability check — 2026-10-27

Before defining a liquidation-event strategy, the official Binance Vision path pattern

`https://data.binance.vision/data/futures/um/daily/liquidationSnapshot/XRPUSDT/XRPUSDT-liquidationSnapshot-YYYY-MM-DD.zip`

was checked for 2022-01-01, 2023-01-01, 2024-01-01, 2025-01-01, 2026-01-01, and 2026-09-30. Every request returned HTTP 404. No liquidation-event price, side, or quantity archive was therefore available from this official free source at the tested dates.

Decision made before any strategy-performance evaluation: do not invent liquidation events, derive them from candle wicks, or silently substitute an unrelated crowding metric. The proposed liquidation strategy is not registered and has no pass/fail result. Research moves to a separately preregistered volatility-compression mechanism using an available price archive. This availability check is about data access only and contains no market-return result.

