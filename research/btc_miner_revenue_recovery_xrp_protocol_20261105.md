# BTC_MINER_REVENUE_RECOVERY_XRP_V1 — frozen protocol

Status: **PREREGISTERED; PERFORMANCE NOT INSPECTED**. Offline PAPER research only.

## Distinct hypothesis

Bitcoin miner revenue is a non-macro, public blockchain-economics observable. A sustained recovery in miner revenue may reduce miner balance-sheet pressure and coincide with improving crypto risk capacity; XRP may then have positive short-horizon drift. This is not a price/volume/flow, XRP-ledger, mempool-clearance, hashrate-shock, ETF, macro, calendar, relative-strength or derivatives hypothesis. It will be evaluated once and will not be inverted or retuned after seeing returns.

## Frozen source and signal

- Source: Blockchain.com chart API, `https://api.blockchain.info/charts/miners-revenue?timespan=all&format=json` (`values[].x` UTC Unix seconds, `values[].y` USD/day).
- Preserve the exact response and SHA256. Reject duplicate/non-increasing timestamps and non-finite or negative observations. Do not interpolate missing observations.
- Availability lag: two actual source observations. A source observation at index `i` may only create an eligible signal at source index `i+2`.
- At each eligible source timestamp, using only observations available after that lag:
  - `recent_7` = arithmetic mean of the latest seven actual observations;
  - `previous_7` = arithmetic mean of the immediately preceding seven actual observations;
  - `prior_90_median` = median of the 90 observations strictly before the latest available observation;
  - signal LONG only when `recent_7 > previous_7` and the latest available miner revenue is above `prior_90_median`.
- A signal date maps only to an XRP candle with the identical UTC date. Missing dates are reported and never filled.

## Frozen execution

- XRPUSDT Binance spot daily OHLC, 2020-01-01 through 2026-09-30 inclusive, fetched from the public Binance data API. Retain exact request URLs, response SHA256 and row counts.
- Entry at the next consecutive daily candle open after a signal candle. Never enter on the signal candle. Signals beyond the price cutoff are counted but not mapped.
- ATR14 from fully closed candles; stop `2.0 × ATR`, target `3R`, maximum hold five daily bars.
- If stop and target are both touched, stop wins. A gap through stop fills at the worse opening price. End-of-fold positions liquidate at the last close.
- Initial equity USD 10,000; risk 0.5% of current equity; notional capped at 20% of current equity; zero leverage; one position; no overlap.
- Base cost: 0.095% fee plus 0.020% adverse slippage per side. Stress doubles both. Costs apply independently to entry and exit.

## Frozen evaluation

- Descriptive control: 2020-01-01 through 2021-12-31.
- Chronological annual-reset OOS folds: 2022, 2023, 2024, 2025 and 2026 through 2026-09-30. A separate continuous 2022–2026 run is diagnostic and is not additional evidence.
- Acceptance gates, all mandatory before forward promotion: at least 75 aggregate annual OOS trades; positive net P/L and expectancy at base and stress; base PF >1.15; stress PF >1.02; at least four positive annual folds at both costs; positive 2026 fold at both costs; continuous conservative marked drawdown <=10% at both costs; no month contributes >25% of total positive monthly profit; independent audit passes.
- `PROŠEL` additionally requires new independent forward PAPER evidence. No historical outcome alone can pass. If historical gates pass but forward evidence is absent, status remains `TEST NEDOKONČEN`.

## Prospective forward gate supplement (2026-11-06, before any forward observation)

The original registration required independent forward PAPER evidence but did not quantify it. Before accepting any post-registration observation, freeze the forward gate as: at least 365 elapsed calendar days after `2026-11-05T19:58:57Z`, at least 20 closed non-overlapping PAPER trades, positive net P/L and expectancy at base and doubled costs, stressed PF >1.0, stressed marked drawdown <=10%, and no single trade above 35% of total positive forward-trade profit. Every source observation and closed XRP candle is frozen on first sight; later revisions stop the runner rather than rewriting evidence. Repeated runs must be idempotent. These requirements may not be weakened after forward results appear.

## Mandatory audits

Source hashes/rows, duplicates, gaps, strict-past 90-observation window, two-observation lag, exact date alignment, next-open timing, ATR past-only use, stop-first ambiguity, gap-stop, end liquidation, fees/slippage, 2× stress, risk/notional cap, one-position/no-overlap, equity reconciliation, marked drawdown, annual/monthly concentration and prefix invariance.

No production code, `main`, `v8-fly-layer-test`, Render, infrastructure, LIVE trading or paused strategy is in scope.
