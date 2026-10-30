# CRYPTO_WEEKLY_INVERSE_VOL_BASKET_V1 — frozen protocol (2026-10-30)

Status: **PREREGISTERED; PERFORMANCE NOT YET EVALUATED.** Offline research only.

## Distinct hypothesis

A continuously invested, long-only basket can reduce concentration in the most volatile crypto asset by allocating equal ex-ante volatility contribution across XRP, BTC and ETH. This is a portfolio-risk mechanism: it uses only the magnitude of each asset's own trailing returns, never return direction or rank. It does not select a winner, predict relative strength, use flow/volume, serial dependence, derivatives, macro, on-chain activity or a volatility breakout.

## Fixed causal rule

Use actual aligned Binance spot XRPUSDT, BTCUSDT and ETHUSDT daily OHLC from January 2020 through September 2026. At each Monday 00:00 UTC open, compute annualized realized volatility from the 30 log returns ending at the preceding daily close. Set raw weights proportional to inverse volatility, cap every asset at 50%, and redistribute excess proportionally among uncapped assets. The three target weights sum to 100%. No return-sign, trend or momentum filter is allowed. Indicators use only closes strictly before the entry open.

## Fixed execution and portfolio accounting

Start each evaluation fold flat with $10,000. At a Monday open, first apply any adverse gap-stop to existing sleeves, then sell remaining sleeves and buy all three target sleeves at that same raw open. Each buy and sell pays 9.5 bps and 2 bps adverse slippage; stress doubles both. Entry budgets account for buy fees, gross notional is at most available equity, each target weight is at most 50%, and there is no leverage or borrowing. Each sleeve has a fixed stop three ATR14 below its adverse entry fill. A gap through the stop sells at the worse open; otherwise an intraday stop sells at the stop, both with adverse slippage and fees. A stopped sleeve remains cash until the next Monday. The final actual close liquidates all sleeves. Daily drawdown marks open sleeves at the candle low after hypothetical exit costs. No target is used.

Exact timestamp alignment is mandatory. Reject duplicates, invalid OHLC, missing days or unequal market calendars; do not interpolate. Retain every request URL, response byte count and locally computed SHA256. Local hashes identify downloaded bytes and are not publisher signatures.

## Locked evaluation and gates

Use 2021 as a control. Annual OOS folds are 2022, 2023, 2024, 2025 and January–September 2026, plus a separate continuous OOS diagnostic. The annual folds reset capital and their trades are the sample for aggregate gates; the continuous run reuses observations and is not additional evidence. No optimization follows the results.

Every historical gate is required: at least 600 completed sleeve trades; positive aggregate net and expectancy with PF >1.15; positive double-cost net and expectancy with PF >1.05; every asset contributes positive aggregate net at both costs; at least 4/5 annual folds are positive at both costs including 2026; continuous base and stress drawdown <=25%; no single year supplies >50% of total positive annual profit; and an independent audit passes source hashes, exact alignment, past-only volatility/ATR, weight arithmetic, chronology, gap-stops, fills, costs, gross/asset caps, overlapping-sleeve accounting, non-overlap per asset, equity reconciliation and reports.

Even a complete historical pass remains `TEST NEDOKONCEN` until at least 180 future calendar days and 75 newly timestamped completed forward PAPER sleeves have positive net and stressed expectancy with no gate change. Code tests or historical profit never mean `PROSEL`. A completed gate failure means `NEPROSEL`; do not alter the 30-day window, weekly schedule, universe, cap or stop on these observations.

Next action: commit this protocol, implementation and mechanics tests remotely before any performance run; then execute the unchanged real-data validation and independent audit. Do not modify production, Render, LIVE, main or `v8-fly-layer-test`.
