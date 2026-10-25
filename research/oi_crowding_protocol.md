# XRP_OI_CROWDING_UNWIND_V1 — frozen protocol (2026-10-25)

Status: **REGISTERED; NOT EVALUATED.** Distinct hypothesis: derivatives positioning, not spot OHLC/volume, funding, basis, calendar or cross-market momentum. A statistically crowded-short XRP perpetual market that simultaneously shows aggressive taker buying and contracting open interest indicates short covering likely to continue briefly.

Data: Binance Vision daily XRPUSDT USD-M `metrics` (open interest, global account long/short ratio, taker long/short volume ratio) plus monthly XRPUSDT spot 5m klines, Jan 2024–Sep 2026. Sort metrics timestamps, reject duplicates/non-5m stamps, intersect with real spot timestamps, retain/report gaps, invent nothing, and require a complete causal 24h metrics lookback.

Fixed signal at closed timestamp: global `count_long_short_ratio` z-score <= -2.0 versus the previous 288 samples (current excluded); `sum_taker_long_short_vol_ratio` >=1.15; open interest is at least 1.0% below 12 samples (one hour) earlier. Enter spot long at next 5m open. ATR36; stop 1.5 ATR; target 2R; max 36 bars. Stop wins ambiguity; gap stop at worse open. Fee 9.5 bps/side, adverse slippage 2 bps/side; stress doubles both. Risk 0.5% equity, notional <=20%, one non-overlapping position, no leverage.

2024 is control. Locked OOS quarters are 2025 Q1–Q4 and 2026 Q1–Q3; continuous OOS is non-independent. All gates: >=150 OOS trades; positive base net/expectancy, PF>1.15; positive stress net/expectancy, PF>1.02; >=5/7 positive quarters including 2026 Q3; continuous base/stress drawdown <=10%; no quarter >40% of positive profit. Historical passage remains `TEST NEDOKONCEN` until >=30 future days and >=100 new PAPER trades pass stressed expectancy. No tuning, LIVE, production, Render, main or deployed changes.

Next: commit this protocol, simulator, tests and provenance runner before downloading/evaluating outcomes.

## Pre-results missing-metric amendment

Initial ingestion stopped before producing any trade or performance result: Binance file `XRPUSDT-metrics-2024-06-12.zip` has an empty `count_long_short_ratio` at 2024-06-12 08:20 UTC. The row will be excluded and reported, never imputed. Timestamp intersection retains a gap and the existing complete-288-sample check suppresses signals crossing it. No signal, exit, cost, sizing or success parameter changes.

A second ingestion-only stop, still before any performance calculation, found 63 rows whose reported `sum_open_interest` is exactly zero. Zero open interest is invalid for the ratio/change signal and will be handled identically to a blank required field: exclude, report, retain gaps, suppress crossing lookbacks. No forward fill or parameter change.

## Completed historical validation — rejected

The amended protocol was frozen before evaluation (SHA256 `baac5292bbfc688c2015f4698efcf04a2f6fc4e9c102b0f9ca8207a10bf180ba`). The run used 1,004 Binance Futures metrics archives and 33 Binance spot kline archives; every source URL, byte count and locally calculated SHA256 is recorded in `oi_crowding_validation_20261025/results.json`. Seventy-one invalid required-metric rows were excluded and reported. Alignment found no metric-only timestamps, 201 spot-only timestamps and no duplicate metric timestamp. Missing observations were not synthesized; exact 288-sample causal windows suppressed signals across gaps.

The seven locked OOS quarters produced 111 base-cost trades, -$579.90, PF 0.5843 and expectancy -$5.22. Doubled costs produced 112 path-dependent trades, -$1,074.52, PF 0.3745 and expectancy -$9.59. Only 2026 Q2 was base-cost positive; final 2026 Q3 lost $203.15. The continuous, non-independent OOS path lost $568.64 with 6.46% maximum drawdown; stress lost $1,030.05 with 11.00% maximum drawdown. Every preregistered gate failed, including the 150-trade sample minimum. No forward PAPER stage is authorized.

All 52 repository unit tests passed. `audit_oi_crowding.py` independently reconciled every ledger with next-5m-open timing, non-overlap, sizing, costs, slippage, P/L and equity and wrote a PASS audit. Passing mechanics do not alter the profitability rejection. Do not retune this strategy on these observed quarters.

Next concrete step: preregister a different mechanism that does not reuse OI/long-short/taker crowding thresholds or previously rejected OHLC continuation, residual, relative-strength, autocorrelation, calendar, stablecoin-peg, flow-pressure or sweep-trend ideas. Keep it offline/PAPER-only and reserve new forward observations before any acceptance decision.
