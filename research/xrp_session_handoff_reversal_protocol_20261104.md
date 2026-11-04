# XRP_ASIA_EUROPE_HANDOFF_REVERSAL_V1 — frozen protocol (2026-11-04)

Status: **PREREGISTERED; PERFORMANCE NOT EVALUATED.** Offline PAPER research only.

## Distinct hypothesis

A sharp XRP decline during the fixed 00:00–08:00 UTC Asian session can reflect temporary regional inventory pressure that mean-reverts after the 08:00 UTC European liquidity handoff. This is a fixed intraday session-transfer hypothesis, not the rejected weekend drift, relative-strength, autocorrelation regime, sweep trend, cross-market residual, volume/flow, derivatives, macro, on-chain, mempool, order-book or volatility-compression rule. It uses no BTC/ETH price, volume, trade count or future bar.

## Fixed signal and timing

Use actual Binance Vision XRPUSDT spot 1h klines. For each UTC date require all eight consecutive, unique closed bars opening 00:00 through 07:00. Asian return is `close(07:00 bar) / open(00:00 bar) - 1`. Signal only when it is <= -1.50%. Enter at the immediately following 08:00 bar open. Any missing/duplicate/misaligned bar suppresses the day; no value is filled. One signal per UTC date, no second price, trend or volatility condition.

## Fixed execution

Long XRPUSDT spot, zero leverage, one position. ATR24 uses the 24 consecutive hourly bars strictly before entry. Stop 1.5 ATR below the adverse entry fill; target 2R; maximum eight bars including entry (08:00–15:59 UTC). Stop wins same-bar ambiguity; a stop gap fills at the worse open and an upward target gap is capped at target. A data gap exits at the last actual pre-gap close. A fold-end position is liquidated at the last in-fold close with costs. Fee 9.5 bps and adverse slippage 2 bps per side; stress doubles both. Risk 0.5% current equity at stop and cap notional at 20%. No shorting, borrowing, funding, overlap or pyramiding.

## Data, chronology and gates

Download official monthly Binance Vision ZIP archives from January 2021 through September 2026. Retain exact URLs, byte counts and local SHA256. Preserve duplicate and gap diagnostics; conflicting duplicates are errors. Calendar 2021 is control. Annual-reset OOS folds are 2022, 2023, 2024, 2025 and January–September 2026; a continuous OOS path is descriptive. No parameter changes after results.

All historical gates are required: >=100 annual-fold OOS trades; positive base net/expectancy and PF>1.20; positive double-cost net/expectancy and PF>1.05; at least 4/5 years positive at both costs including 2026; continuous base/stress drawdown <=10%; no exit month >25% of positive monthly profit; and an independent audit passing source hashes, timestamp uniqueness, exact session bars, strict next-open entry, ATR, stop/target/gap priority, sizing, fees, slippage, non-overlap, equity, drawdown and aggregation.

Even a historical pass remains `TEST NEDOKONCEN` until at least 365 new future days and 100 newly timestamped PAPER trades show positive base and stressed expectancy under unchanged rules. A failed historical gate means `NEPROSEL`. Do not tune the -1.50% threshold, sessions, direction or hold after viewing results.

Next action: remotely commit this protocol, implementation, downloader, audit and tests before downloading the fixed archives. Production, Render, main, LIVE, paused strategies and `v8-fly-layer-test` remain untouched.
