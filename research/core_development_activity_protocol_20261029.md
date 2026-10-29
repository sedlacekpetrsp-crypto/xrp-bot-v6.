# XRP_CORE_DEVELOPMENT_ACTIVITY_V1 — preregistration (2026-10-29)

Status: HYPOTHESIS REGISTERED; PERFORMANCE NOT YET EVALUATED. This document is not evidence of profitability.

## Distinct hypothesis

Sustained public integration of code into the canonical XRPL server repository is an observable fundamental-development signal. XRP spot is bought only when both short and monthly counts of actually merged pull requests show continuing core-development activity. This uses official public merge timestamps, not commit author dates, price/volume/flow, relative strength, sentiment, DeFi yield, on-chain usage, derivatives positioning or a macro-market proxy.

No repository, count threshold, lookback, exit, test period or acceptance gate may be changed after this commit based on returns.

## Frozen sources and causal alignment

- Development source: official GitHub REST Search Issues API for repository `XRPLF/rippled`, queries restricted to `is:pr is:merged` and non-overlapping calendar-year merged-date ranges. Paginate at 100 results until every reported item is captured.
- Use only each item's immutable PR number and public `pull_request.merged_at`; ignore commit author/committer dates, updates, comments, issue close times and non-merged PRs.
- Retain every exact query URL, response bytes, retrieval time, SHA256, reported total count, page count and PR identity. Reject conflicting duplicate PR numbers or merged timestamps. A duplicate returned by API pagination may be removed only if byte fields used here are identical.
- Price source: actual Binance Vision monthly XRPUSDT spot daily kline ZIPs, January 2020 through September 2026, with exact URL/SHA256/row/gap manifest.
- Aggregate merge events by UTC calendar day. A signal calculated for day D uses merge timestamps no later than 23:59:59.999 UTC on D and may enter only at XRP daily open D+1. No event or price is forward-filled or invented.
- Require uninterrupted XRP candles through ATR warmup and the position. Preserve gaps; a position meeting a gap exits at the last real close before it.

## Frozen signal and execution

At the close of every UTC day D:

1. count merged PRs during D-6 through D inclusive; require at least 5;
2. count merged PRs during D-29 through D inclusive; require at least 15.

If both conditions hold, schedule a long XRPUSDT spot order at the next daily open. Signals during an open position are ignored. There is no shorting, leverage, pyramiding, repository substitution, contributor weighting, PR-size filter or parameter search.

- ATR(14) from fully closed XRP daily candles through D.
- Entry: next daily open plus adverse slippage.
- Stop: entry minus 2.0 ATR.
- Target: entry plus 3.0 times initial stop distance.
- Maximum holding: 10 daily bars, exiting at the tenth close.
- Intrabar ambiguity: stop wins. Gap through stop fills at the worse open plus adverse exit slippage; a gap through target receives no better than target.
- Base fee 0.095% per side and adverse slippage 0.02% per side; stress doubles both.
- Each independent fold starts at USD 10,000. Risk 0.5% of current equity to the initial stop before costs, capped at 20% equity notional. Zero leverage and one position maximum.

## Frozen chronology and acceptance

Source/training control: 2020-01-01 through 2021-12-31. Locked exploratory annual OOS folds: 2022, 2023, 2024, 2025 and 2026 through the last complete Binance monthly archive. Each fold starts flat; a continuous OOS path is descriptive, not independent evidence. These market dates were inspected by earlier hypotheses, so there will be no tuning on them.

Historical promotion requires all of:

- at least 75 annual-fold OOS trades;
- positive aggregate net P/L and expectancy at base and double costs;
- aggregate PF >1.20 base and >1.05 stress;
- at least four of five OOS years positive at base and stress, including 2026;
- continuous max drawdown <=10% base and stress;
- no calendar month supplies more than 40% of total positive-month profit;
- independent audit passes exact merge completeness, causality, source-to-entry timing, no overlap, sizing/cap, costs, gap-stop, equity and hash reconciliation.

Even a full historical pass remains only a forward-PAPER candidate. `PROŠEL` additionally requires at least 30 later calendar days and 75 genuinely new timestamped forward-PAPER trades with positive base and stressed expectancy under unchanged rules. Historical replay is never forward evidence.

## Next action

Record source feasibility and complete official GitHub pagination before looking at returns. Then implement tests, download and hash sources, run control/OOS/stress simulations and an independent audit, saving full ledgers and a decision. Do not change production, main, `v8-fly-layer-test`, Render, paused strategies or LIVE trading.
