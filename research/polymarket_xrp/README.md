# POLYMARKET_XRP_SIGNAL_V1

Offline PAPER research only. No imports from production bots, no order submission,
no Render changes, no workflow, no new dependencies or paid services.

## Hypothesis

Use a timestamped Polymarket XRP five-minute Up probability as a directional
filter for Binance XRPUSDT spot. Buy only if probability exceeds a threshold
and Binance price momentum over the preceding 60 seconds is positive. Sell at
the end of the five-minute window. Long/cash only, no leverage. Each trade uses
the current simulated equity. This is an exploratory candidate, not a calibrated
probability model or a cross-exchange arbitrage implementation.

Choose threshold from 0.55/0.60/0.65/0.70 on chronological training data only;
freeze it for the held-out period. Purge windows crossing the split. Default
assumptions: 10 bps fee and 5 bps slippage PER SIDE, plus a double-cost scenario.
These are assumptions, not verified account-specific fees or measured fills.

## Reproduce

From repository root:

```sh
python research/polymarket_xrp/probe.py
python -m unittest discover -s research/polymarket_xrp -v
python research/polymarket_xrp/strategy.py aligned.csv --cutoff UNIX_SECONDS
```

CSV fields are listed in `strategy.FIELDS`. All times are UTC seconds.
`window_start` comes from the five-minute market slug, not Gamma creation time.
`p_up` must map to the Up token using Gamma outcomes and clobTokenIds.
`poly_ts` must be the time the observation was available, not a later settlement.
`binance_ts` is the timestamp of signal_price, at or before signal_ts;
past_price must be from 60 seconds before signal_ts. Entry is strictly after
signal_ts, exit at window end (up to five seconds execution delay).
Use executable quotes/trades for entry/exit prices and retain raw provenance.
Do not use an unfinished candle's eventual close as a signal or execution price.
The CSV validator cannot authenticate provenance or availability semantics.

Drawdown reported by the harness is CLOSED-TRADE equity drawdown only;
intratrade mark-to-market maximum drawdown requires additional data.
Further requirements before claiming an edge: adequately sized independent
sample, coverage/missingness audit, momentum-only baseline, uncertainty estimates,
mark-to-market risk, multiple testing adjustment and prospective PAPER validation.
The harness intentionally never promotes exploratory PnL to a PROŠEL verdict.

## Actual result, 2026-10-28

TEST NEDOKONČEN. Seven synthetic correctness tests pass; historical strategy
backtest has NOT run. Zero historical trades evaluated. Net return and maximum
drawdown are unavailable, not zero. No out-of-sample performance obtained.

Resolved GitHub access: actual repository name is `xrp-bot-v6.` (trailing dot).
Binance standard API returned 451; official public-data endpoint
`https://data-api.binance.vision` returned actual XRPUSDT candles (200).
September archive at data.binance.vision also returned ZIP bytes (200), but
full archive was not downloaded or validated.
Gamma search identified `xrp-updown-5m-1773952800`; exact market fetch returned
200. Its Up token is recorded by probe.py. Both CLOB and Data API history
requests for that exact token/window returned 403. No usable historical
Polymarket probabilities were obtained. These responses describe this execution
environment, not a claim that historical data is unavailable everywhere.

`api_probe.json` preserves returned data, request URLs, errors and retrieval times.
The next required input is genuine timestamped Polymarket history, obtained via
an accessible public endpoint or a user-provided export, with enough matching
Binance data. Do not substitute Binance direction for missing Polymarket signals.

Official references:
- https://developers.binance.com/en/docs/products/spot/rest-api
- https://institute.polymarket.com/data
- https://data-api.polymarket.com/v2/docs
