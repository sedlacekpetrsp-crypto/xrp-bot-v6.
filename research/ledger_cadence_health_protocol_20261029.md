# XRP_LEDGER_CADENCE_HEALTH_V1 — preregistration (2026-10-29)

Status: HYPOTHESIS REGISTERED; PERFORMANCE NOT YET EVALUATED. This is not evidence of profitability.

## Distinct hypothesis

Consistently healthy XRP Ledger close cadence is an infrastructure-quality regime: reliable settlement capacity may support sustained XRP demand, while degraded consensus cadence should suppress exposure. This tests protocol block/ledger production, not transaction or address activity, fees, price/volume/flow, relative strength, sentiment, DeFi, developer activity, derivatives or macro markets.

No threshold, lookback, lag, exit, test period or gate may be changed after this commit based on returns.

## Frozen source and alignment

- Metric: CoinMetrics Community XRP daily `BlkCnt` at `https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=xrp&metrics=BlkCnt&frequency=1d&page_size=10000`.
- Price: actual Binance Vision monthly XRPUSDT spot daily kline ZIPs, January 2020 through September 2026.
- Save exact URLs, retrieval timestamps, payload/archive bytes, rows and local SHA256. Hashes identify downloaded bytes and are not publisher-signed.
- Require unique increasing UTC dates. Preserve all gaps and never fill/interpolate a metric or price.
- A metric labelled day D is treated as unavailable throughout D+1 and may first schedule entry at the XRP daily open of D+2. This conservative full-calendar-day publication lag prevents use of an incompletely formed daily metric.
- Every signal feature uses metric day D and earlier only. ATR uses fully closed XRP candles through D+1.

## Frozen signal and execution

For metric day D after sufficient history:

1. median `BlkCnt` of D-13 through D inclusive must be at least 21,600 ledgers/day (a four-second average cadence);
2. minimum `BlkCnt` of D-6 through D inclusive must be at least 20,000 (no recent day slower than 4.32 seconds on average).

If both hold and the exact D+2 XRP candle exists with uninterrupted ATR history, buy XRPUSDT spot at its open. Signals during an open position are ignored. No shorting, leverage, pyramiding, price trend filter, percentile fitting or parameter search.

- ATR(14), stop 2.0 ATR, target 3.0 times initial stop distance.
- Maximum holding 10 daily bars, exit at the tenth close.
- Intrabar ambiguity: stop wins. Gap through stop fills at the worse open plus adverse exit slippage; target gaps receive no better than target.
- Base fee 0.095% per side and adverse slippage 0.02% per side; stress doubles both.
- Each fold starts with USD 10,000. Risk 0.5% current equity to initial stop before costs, capped at 20% notional. Zero leverage and one position maximum.

## Frozen chronology and acceptance

Source/training control: 2020-01-01 through 2021-12-31. Locked exploratory annual OOS folds: 2022, 2023, 2024, 2025 and 2026 through the last complete Binance monthly archive. Annual folds reset equity; continuous OOS is descriptive and not independent. These prices were inspected before, so no tuning is allowed.

Historical promotion requires:

- at least 150 aggregate annual-fold OOS trades;
- positive aggregate net P/L and expectancy at base and double costs;
- aggregate PF >1.20 base and >1.05 stress;
- at least four of five OOS years positive at base and stress, including 2026;
- continuous max drawdown <=10% base and stress;
- no month supplies more than 25% of total positive-month profit;
- independent audit passes metric lag, exact-date alignment, gaps, hashes, fills, costs, sizing, non-overlap and equity reconciliation.

Even a historical pass remains a forward-PAPER candidate only. `PROŠEL` additionally requires at least 30 later calendar days and 100 genuinely new timestamped forward-PAPER trades with positive base and stressed expectancy under unchanged rules. Historical replay is not forward evidence.

## Next action

Commit source feasibility, implement unit tests and runner, download exact raw sources, run control/OOS/stress simulations and independent audit, and save full ledgers and decision. Do not change production, main, `v8-fly-layer-test`, Render, paused strategies or LIVE trading.
