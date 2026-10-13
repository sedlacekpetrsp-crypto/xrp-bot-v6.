# Blue Whale VWAP Reversion — 13 October 2026

Verified in persisted state: SOLUSDT SHORT opened 01:44:20 UTC, closed 01:52:01 at SL, net -9.606055431754605 USDT. ETHUSDT SHORT opened 01:53:21 UTC, closed 02:06:52 at SL, net -10.806222677008206. Entry plus exit fees total 7.981952416909644. Neither position remains open.

The production score admitted both SHORT candidates with hourly RSI 11.3004 and 13.8786 despite positive 5m ret3 (+0.00556 and +0.00109). The hourly structural veto did not reject them; additive confirmations elsewhere still reached score 4. This is a concrete entry-quality weakness, not statistical proof of a profitable alternative.

New entries in VWAP_REVERSION are paused at both scanner dispatch and the open_paper entry boundary. Existing position exit management is unchanged. FIB, VWAP_TREND_RECLAIM and 4h trendline keep their existing rules and risk. The shared dashboard shows the pause even when no candidate appears.

Candidate scans continue and retain a SHADOW_REVIEW: hourly RSI extremes (<20 SHORT, >80 LONG), aligned 5m EMA20/50 and signed 3-bar return, plus net target rate and net target/fees under existing execution costs. These are review hypotheses, not promoted live filters. Diagnostics record missing indicator data and explicitly set profitability_verified=false. They neither debit the account nor claim a counterfactual profit. No risk or stop-loss is expanded.

A longer cost-inclusive replay with unused or future validation data is still required before reactivation. Two losing trades cannot establish that an RSI threshold is profitable. Other previously paused bots remain paused, and NEWS_LONG retains its independent account and RSS worker.

## Follow-up: retaining usable evidence

The 500-entry rolling scan journal covered only about one hour at 04:44 UTC (500 observations, six actual candidate observations, six distinct candidate keys). It could not support a meaningful long-term filter review. A separate compact candidate_journal now retains up to 1000 distinct (symbol,strategy,key) candidates, counting repeated observations without evicting them due to routine WAIT scans. The still-available candidate observations are backfilled at startup using their original timestamps and recorded scan marks.

Public quote updates collect signed mark moves at 15, 60 and 240 minutes with actual observation times, alongside sparse favorable/adverse excursions. Quotes more than five minutes late are marked missed without an inferred return. Marks are not trade fills, outcomes do not reproduce intrabar SL/TP paths, and no profitability claim is made. Trading remains paused for VWAP Reversion. Data is persisted in the existing state and exposed only through /whale/candidate-journal, keeping the routine dashboard response small.

Thirty-six focused tests pass for distinct identity, repeat handling, WAIT scan retention, bounded capacity, persistence payload, horizons, delayed/invalid quotes, signed moves, pause guards, account nonmutation and independent NEWS behavior. No filter is promoted from the small sample.
