# BTC_ETF_CREATION_IMPULSE_XRP_V1 — frozen protocol (2026-10-30)

Status: **PREREGISTERED; PERFORMANCE NOT YET EVALUATED.** Offline research only.

## Distinct hypothesis and source feasibility

Positive net primary-market flow into the US spot-Bitcoin ETF complex represents institutional cash demand that may persist into broad crypto risk appetite and XRP over the following days. This mechanism uses date-stamped ETF creations/redemptions rather than price direction, relative strength, exchange volume, derivatives positioning, macro data, on-chain activity, network security or any previously rejected family.

The free Farside Investors “Bitcoin ETF Flow — All Data” page exposes daily per-fund and total US-dollar flows from 11 January 2024. It is reproducible as a single HTML response and will be retained byte-for-byte with its URL and local SHA256. Farside is a regulated investment firm but the compilation is not an issuer filing or an audited primary source; that limitation is permanent and independently prevents treating a historical pass as deployment evidence. Use only the page-reported `Total`; a dash is missing, never zero. Exclude an incomplete row or any row after 30 September 2026. Never fill a missing flow day or infer a value from fund AUM.

## Fixed causal rule and execution

For every reported flow date D with a finite `Total` strictly greater than USD 0 million, create one signal. Because publication follows the US session and its exact historical release time is unavailable, enter XRPUSDT only at the UTC open on D+2 calendar days. Non-reported dates create no signal. There is no flow threshold search, rolling normalization or price filter.

Long XRP spot, zero leverage, one position. ATR14 uses only preceding closed daily XRP candles. Stop two ATR below the adverse entry fill, target 3R, maximum five candles including entry. Stop wins same-candle ambiguity; a downward gap through stop fills at the worse open and an upward target gap is capped at target. Fee 9.5 bps and adverse slippage 2 bps per side; stress doubles both. Risk 0.5% current equity at stop and cap notional at 20%. Signals during an open position are skipped. A price gap forces exit at the last actual pre-gap close. No synthetic prices, borrowing or funding.

## Locked evaluation and gates

Use actual Binance XRP daily spot prices through 30 September 2026. The control is 11 January–30 June 2024. Locked OOS folds are 2024-H2, 2025-H1, 2025-H2, 2026-H1 and 2026-Q3, each reset to USD 10,000; a separate continuous OOS path is descriptive and not an additional independent sample. Preserve raw source responses, all signals/trades and an implementation-independent audit. No tuning follows results.

Every historical gate is required: at least 100 aggregate OOS trades; positive base net and expectancy with PF>1.20; positive doubled-cost net and expectancy with PF>1.05; at least four of five folds positive at both costs including 2026-Q3; continuous base and stress drawdown <=10%; no month supplies more than 25% of total positive monthly profit; and an independent audit of hashes, parsing, missing markers, two-day lag, OHLC, ATR, fills, costs, sizing, gap-stop, non-overlap, equity and reports.

Even a complete historical pass remains `TEST NEDOKONCEN` until at least 180 future calendar days and 30 newly timestamped forward PAPER trades show positive base and doubled-cost expectancy with unchanged rules and independently retained source snapshots. Tests and historical profit never mean `PROSEL`. A completed failed historical gate means `NEPROSEL`; do not change the sign, lag, hold, or flow definition on these observations.

Next action: commit this protocol, implementation, downloader, audit and tests remotely before performance; then run the unchanged validation. Do not touch production, Render, LIVE, main, paused strategies or `v8-fly-layer-test`.
