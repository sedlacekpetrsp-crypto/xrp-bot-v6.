# Expanded historical-data search — 2026-10-28

Verdict remains TEST NEDOKONČEN. No historical strategy performance has been measured.
HTTP 403 indicates access refusal from this environment; it does not establish that a provider does not publish history.

## Directly inspected XRP CSV

https://github.com/felixdoteth/polymarket-crypto-5m-dataset

README advertises 18,966 XRP windows. Raw CSV request returned HTTP 200 and its beginning was inspected, not the full dataset. Header:
`timestamp,slug,outcome,up_token,down_token,btc_open,btc_close,btc_change_pct,date,hour_utc,minute`

First XRP row contains btc_open=72815.25. These BTC columns must not be interpreted as XRP prices. There are no pre-resolution Polymarket price/probability observations. Useful potentially for token mapping and resolution labels, subject to validation; not sufficient for the requested signal backtest.

## pmxt public event archive

https://archive.pmxt.dev/docs/v2-data-overview

Provider documents public, credential-free hourly Parquet files of WebSocket events, not merely one snapshot per hour. Fields include source and receipt timestamps, asset_id, bid/ask and book updates. Coverage of our XRP tokens still needs checking.

Actual local probes: archive listing returned HTTP 503. Range GET of bytes 0–3 on both
https://r2v2.pmxt.dev/polymarket_orderbook_2026-09-09T15.parquet
and
https://r2v2.pmxt.dev/polymarket_orderbook_2026-04-17T12.parquet
returned HTTP 403. No Parquet content obtained. License advertised CC BY 4.0, credit pmxt if used.

## Resolved Markets

https://resolvedmarkets.com/polymarket-historical-data
https://resolvedmarkets.com/pricing

Provider explicitly advertises XRP crypto up/down order books including 5m, history since March 2026, and Free plan with 5,000 credits/month and full depth/history. Historical snapshot requests cost 5 credits according to pricing. API key required; no account created, key obtained or dataset downloaded. Hosted backtesting is not included in Free; our own local offline test would use exported data. Availability, gaps and sufficient free quota remain unverified.

## PMData

https://pmdata.dev/polymarket-crypto-data
https://pmdata.dev/docs/api-reference

Provider advertises XRP Up/Down tick data. Documented authenticated ZIP route:
`https://api.pmdata.dev/v1/polymarket/l2/YYYY/MM/DD/xrp-5m.zip`
Free accounts may download Polymarket data older than 21 days. One 5m daily ZIP costs 72 quota units; repeated downloads consume quota. Chainlink data requires a paid plan, so excluded. No account created or data downloaded.

## Next executable path

Obtain an authorized free-provider export or restore access to pmxt files, audit actual XRP coverage and timestamps, then build aligned data. Never use final market outcomes as earlier probability signals. Paid services, production deployment and LIVE trading remain excluded. Nothing is running in the background to monitor availability.
