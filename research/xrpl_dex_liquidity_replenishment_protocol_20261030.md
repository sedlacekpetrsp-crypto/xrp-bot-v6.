# XRPL_DEX_LIQUIDITY_REPLENISHMENT_V1 — frozen protocol (2026-10-30)

Status: **PREREGISTERED; PERFORMANCE NOT YET EVALUATED.** Offline research only.

## Distinct hypothesis and source

Growth in explicitly funded, two-sided XRP liquidity on the native XRP Ledger DEX can represent improving market quality and willingness to warehouse XRP inventory, preceding positive spot expectancy. This tests absolute decentralized-liquidity replenishment, not the rejected Binance futures depth imbalance, exchange volume, price/relative strength, ETF flow, derivatives, macro, network-security or aggregate on-chain count families. It never uses a bid/ask imbalance sign.

Use immutable historical ledger and `book_offers` responses from the public full-history `https://xrplcluster.com/` JSON-RPC endpoint for XRP/GateHub USD (`rhub8VRN55s94qWKDv6jmDy1pUykJzF3wq`). Preserve every request, ledger hash, response byte count and local SHA256. GateHub USD is issuer credit, not fiat in custody of this study; its issuer and venue risks are permanent limitations. The retired aggregate `data.ripple.com` endpoint returned HTTP 403, so no executed trade, spread or volume is inferred from it.

## Fixed observations and signal

Sample ledger indices 60,000,000, 60,120,000, ... through 107,400,000: a fixed 120,000-ledger cadence chosen before performance, independent of calendar prices. Request 400 offers in each direction. Use only offers carrying a finite positive `owner_funds` field; ignore absent or zero funding rather than assuming it. Convert drops exactly at 1,000,000 drops/XRP. Best funded ask and bid define mid and proportional spread. Sum explicitly funded XRP executable within 2% of mid on both sides. A snapshot is invalid if either side is empty, bid >= ask, spread >2%, or a 400th returned offer remains inside the 2% depth band (truncated relevant depth). Do not paginate after evaluation or fill an invalid snapshot.

A signal exists only when the current and immediately preceding indices are both valid and exactly 120,000 apart, current total two-sided 2%-depth is strictly greater than prior depth, and current spread is <=2%. There is no magnitude threshold, side imbalance, price trend or optimization. Enter at the first XRP UTC daily open at least 48 hours after the ledger close; the current entry price cannot affect the signal.

## Fixed execution

Long XRP spot, zero leverage, one position. ATR14 uses preceding closed daily Binance XRPUSDT candles. Stop two ATR below adverse entry fill, target 3R, maximum five candles including entry. Stop wins same-candle ambiguity; gap stop fills at the worse open and an upward target gap is capped at target. Fee 9.5 bps and adverse slippage 2 bps per side; stress doubles both. Risk 0.5% current equity at stop and cap notional at 20%. Skip signals during an open position. A price gap exits at the last actual pre-gap close. No synthetic prices, borrowing or funding.

## Locked evaluation and gates

Use actual Binance daily XRP prices January 2021–September 2026. Calendar 2021 is control. Annual-reset OOS folds are 2022, 2023, 2024, 2025 and 2026 through September; a separate continuous OOS path is descriptive. Preserve derived observations, source provenance, all ledgers and an implementation-independent audit. No tuning follows results.

All historical gates are required: >=100 annual-fold OOS trades; positive base net/expectancy and PF>1.20; positive double-cost net/expectancy and PF>1.05; >=4/5 years positive at both costs including 2026; continuous base/stress drawdown <=10%; no month >25% of total positive monthly profit; and a passing independent audit of response hashes, ledger cadence/hashes/times, funded-offer parsing, depth, spread, 48-hour lag, OHLC, ATR, fills, costs, sizing, gaps, non-overlap, equity and reports.

Even a historical pass remains `TEST NEDOKONCEN` until >=365 future days and >=30 newly timestamped forward PAPER trades have positive base and stressed expectancy with unchanged rules and retained source responses. Tests and historical profit never mean `PROSEL`. A completed failed gate means `NEPROSEL`; do not change the issuer, cadence, 2% band, growth sign or spread rule on these observations.

Next action: commit this protocol, implementation, downloader, audit and tests remotely before querying the full frozen ledger sequence. Do not touch production, Render, LIVE, main, paused strategies or `v8-fly-layer-test`.
