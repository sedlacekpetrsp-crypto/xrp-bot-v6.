# Issue 56 diagnostic protocol (no performance test)
Fixed window: 2026-11-12 14:00 UTC < candle close <= 2026-11-13 14:00 UTC.
Use public Binance spot XRPUSDT closed 5m/15m/1h bars, max 250 bars per timeframe per evaluation (same as runtime), warmup >=55 bars. Count valid 5m, sweep/reclaim, aligned 15m/1h trend, volume >=1.05, setup signals. No trades simulated, no PnL, no parameter search.
Historical contemporaneous futures observations and arrival times are not archived: futures 3/3, execution guards and entries attributable to this window must be UNKNOWN, never inferred from current observations. Runtime SQL and status are separate point-in-time evidence.
Store inputs and hashes, use an offline repeatable script. No production write, merge, deploy, workflow dispatch or live order.
