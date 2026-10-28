# FRED broad-dollar source check — 2026-10-28

Checked before performance evaluation of `XRP_BROAD_DOLLAR_DOWNTREND_V1`.

The fixed direct source is:

`https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTWEXBGS&cosd=2020-01-01&coed=2026-10-01`

The feasibility request returned HTTP 200 and CSV content with columns
`observation_date,DTWEXBGS`, beginning 2020-01-02 and ending 2026-10-01.
This check established only availability, schema and coverage; it did not join
XRP prices, evaluate signals or calculate returns. The validation runner will
independently download and hash the raw CSV and will retain its exact URL, byte
count, SHA256, observation count, missing-value dates and exclusions.

FRED observations use a business-day calendar and can be revised. Weekends and
holidays will not be filled. To guard against release timing, a value will not
be usable until the date of the second subsequent actual FRED observation.
