# XRP_OI_CROWDING_UNWIND_V1 — frozen protocol (2026-10-25)

Status: **REGISTERED; NOT EVALUATED.** Distinct hypothesis: derivatives positioning, not spot OHLC/volume, funding, basis, calendar or cross-market momentum. A statistically crowded-short XRP perpetual market that simultaneously shows aggressive taker buying and contracting open interest indicates short covering likely to continue briefly.

Data: Binance Vision daily XRPUSDT USD-M `metrics` (open interest, global account long/short ratio, taker long/short volume ratio) plus monthly XRPUSDT spot 5m klines, Jan 2024–Sep 2026. Sort metrics timestamps, reject duplicates/non-5m stamps, intersect with real spot timestamps, retain/report gaps, invent nothing, and require a complete causal 24h metrics lookback.

Fixed signal at closed timestamp: global `count_long_short_ratio` z-score <= -2.0 versus the previous 288 samples (current excluded); `sum_taker_long_short_vol_ratio` >=1.15; open interest is at least 1.0% below 12 samples (one hour) earlier. Enter spot long at next 5m open. ATR36; stop 1.5 ATR; target 2R; max 36 bars. Stop wins ambiguity; gap stop at worse open. Fee 9.5 bps/side, adverse slippage 2 bps/side; stress doubles both. Risk 0.5% equity, notional <=20%, one non-overlapping position, no leverage.

2024 is control. Locked OOS quarters are 2025 Q1–Q4 and 2026 Q1–Q3; continuous OOS is non-independent. All gates: >=150 OOS trades; positive base net/expectancy, PF>1.15; positive stress net/expectancy, PF>1.02; >=5/7 positive quarters including 2026 Q3; continuous base/stress drawdown <=10%; no quarter >40% of positive profit. Historical passage remains `TEST NEDOKONCEN` until >=30 future days and >=100 new PAPER trades pass stressed expectancy. No tuning, LIVE, production, Render, main or deployed changes.

Next: commit this protocol, simulator, tests and provenance runner before downloading/evaluating outcomes.

## Pre-results missing-metric amendment

Initial ingestion stopped before producing any trade or performance result: Binance file `XRPUSDT-metrics-2024-06-12.zip` has an empty `count_long_short_ratio` at 2024-06-12 08:20 UTC. The row will be excluded and reported, never imputed. Timestamp intersection retains a gap and the existing complete-288-sample check suppresses signals crossing it. No signal, exit, cost, sizing or success parameter changes.
