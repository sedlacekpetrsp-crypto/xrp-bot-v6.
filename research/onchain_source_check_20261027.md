# On-chain source feasibility — 2026-10-27

The unauthenticated Ripple Data API returned `Missing Authentication Token`, so
it is not used and no paid service is added. CoinMetrics Community directly
returned dated XRP `AdrActCnt` and `TxCnt` observations without credentials.
The protocol therefore freezes CoinMetrics Community as the on-chain source and
adds a full-day availability lag before a metric can affect a signal.

Checked endpoint family:
`https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=xrp&metrics=TxCnt,AdrActCnt&frequency=1d`

Availability is not evidence of completeness or profitability; validation must
retain hashes and stop rather than invent a missing observation.
