# VWAP Reversion validation — 13 October 2026

Decision: **no tested replacement is eligible for promotion; VWAP_REVERSION remains paused.**

Scope: ETHUSDT and SOLUSDT spot, 141,720 validated minute candles total, 25 August–13 October 05:00 UTC. The warmup is excluded from trading. Development is 1–20 September; chronological check is 21 September–13 October 05:00 UTC. Both portfolios independently start at 10,000 USDT. The hypotheses came from 13 October losing trades, so the check includes data that informed the hypotheses and is not an unseen holdout. No thresholds were added after results.

| Variant | Development net | Development trades | Check net | Check trades | Check PF | Check with 2x slip |
|---|---:|---:|---:|---:|---:|---:|
| baseline | -8.89 | 1 | 6.43 | 2 | 1.730 | -8.50 |
| rsi_extremes | -8.89 | 1 | 15.23 | 1 | — | 0.00 |
| rsi_and_5m_continuation | 0.00 | 0 | 0.00 | 0 | — | 0.00 |

Net figures include production modeled costs, 0.095% fee and 0.02% slippage per side. RSI review blocks SHORT below 20 and LONG above 80. Continuation also requires aligned closed 5m EMA20/50 and signed three-bar return. Source technical score threshold is 4, matching the recorded recent trades. The RSI is the source simple rolling RSI implementation, not an assumed alternative indicator.

Baseline has only three trades over both periods; the RSI-only variant has two; continuation has zero. Zero trades does not demonstrate profitability. The minimum-30-trade gate, positive results on both symbols and stress-cost gate all prevent promotion. Raw candidate scans are not independent trades. Most candidates fail the existing minimum stop-distance or cost-inclusive RR gates.

## Replay fidelity and specific failure to reproduce a live fill

The runner uses production vwap_candidate, technical_confirmation, entry validation, sizing, cost accounting and close_paper. Trading and persistence are disabled in this offline process. VWAP_TREND_RECLAIM/FIB/trendline are excluded so this is a standalone reversion experiment. News history is unavailable and excluded; other portfolio strategies are not simulated. Entries use the next minute open; only completed bars inform decisions. Stops precede targets in ambiguous bars, adverse gaps fill at open, cost-covered break-even updates at close for the next bar. Equity drawdown is sampled at minute closes. No financing, news or latency reconstruction is claimed.

**The minute-open fill model fails to reproduce the recorded ETH trade.** Its signal candidate and hourly RSI matched exactly at 01:53 UTC, but the minute-open model gives stop distance 0.162852%, below the 0.2% floor. The recorded entry at 01:53:21 gives 0.206776%, above the floor. Thus the simulation omits a known losing live trade. See point_checks.json. The superficially positive check result cannot override this fidelity issue. An accurate replacement assessment requires finer execution observations and a prospective period. The existing candidate evidence records sampled marks, not a complete tick-level execution history.

## Reproduction and checks

`python research/whale_vwap_validation_20261013/download.py /tmp/whale-data` then `python research/whale_vwap_validation_20261013/run.py /tmp/whale-data`. Source commit, parameters, boundaries, SHA256 manifests, aggregate results and individual simulated trades are retained. Source data and derived signal cache are excluded from the branch.

Fifteen focused tests pass: closed-only inputs, hypothesis gating, simultaneous stop/target ordering, honest gap fills and cost reconciliation, plus candidate retention and production reversion pause checks. These tests do not establish profitability. No running strategy, risk, balance or deployment is changed by this research.
