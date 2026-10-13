# Blue Whale VWAP Reversion — 13 October 2026

Verified in persisted state: SOLUSDT SHORT opened 01:44:20 UTC, closed 01:52:01 at SL, net -9.606055431754605 USDT. ETHUSDT SHORT opened 01:53:21 UTC, closed 02:06:52 at SL, net -10.806222677008206. Entry plus exit fees total 7.981952416909644. Neither position remains open.

The production score admitted both SHORT candidates with hourly RSI 11.3004 and 13.8786 despite positive 5m ret3 (+0.00556 and +0.00109). The hourly structural veto did not reject them; additive confirmations elsewhere still reached score 4. This is a concrete entry-quality weakness, not statistical proof of a profitable alternative.

New entries in VWAP_REVERSION are paused at both scanner dispatch and the open_paper entry boundary. Existing position exit management is unchanged. FIB, VWAP_TREND_RECLAIM and 4h trendline keep their existing rules and risk. The shared dashboard shows the pause even when no candidate appears.

Candidate scans continue and retain a SHADOW_REVIEW: hourly RSI extremes (<20 SHORT, >80 LONG), aligned 5m EMA20/50 and signed 3-bar return, plus net target rate and net target/fees under existing execution costs. These are review hypotheses, not promoted live filters. Diagnostics record missing indicator data and explicitly set profitability_verified=false. They neither debit the account nor claim a counterfactual profit. No risk or stop-loss is expanded.

A longer cost-inclusive replay with unused or future validation data is still required before reactivation. Two losing trades cannot establish that an RSI threshold is profitable. Other previously paused bots remain paused, and NEWS_LONG retains its independent account and RSS worker.
