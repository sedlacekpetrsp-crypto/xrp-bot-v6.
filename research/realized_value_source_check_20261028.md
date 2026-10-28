# CoinMetrics XRP realized-value source check — 2026-10-28

Checked before performance evaluation of `XRP_REALIZED_VALUE_DISCOUNT_V1`.

The direct CoinMetrics Community catalog endpoint
`https://community-api.coinmetrics.io/v4/catalog-all/assets?assets=xrp`
lists daily `CapMVRVCur` with community availability. The frozen query is:

`https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=xrp&metrics=CapMVRVCur&frequency=1d&start_time=2020-01-01&end_time=2026-10-01&page_size=10000`

The feasibility response returned HTTP 200, 2,466 rows, no pagination token,
first date 2020-01-01 and last date 2026-10-01. This check established only
availability, schema and coverage; it did not join prices or calculate strategy
returns. The validation runner will download and hash its own raw response and
will record exact source URLs, byte counts, SHA256, gaps and exclusions.

`CapMVRVCur` is a third-party derived metric and its historical methodology may
change. The test treats each dated value as unavailable until the following
daily close and never interpolates or forward-fills it.
