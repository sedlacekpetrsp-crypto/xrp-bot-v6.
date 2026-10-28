# FRED VIX source check — 2026-10-28

Checked before performance evaluation of `XRP_VIX_SHOCK_RECOVERY_V1`.

The fixed direct source is:

`https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS&cosd=2020-01-01&coed=2026-10-01`

The feasibility request returned HTTP 200 and CSV content with columns
`observation_date,VIXCLS`, beginning 2020-01-02 and ending 2026-10-01.
This check established only availability, schema and coverage; it did not join
XRP prices, evaluate signals or calculate returns. The validation runner will
independently download and hash the raw CSV and retain its exact URL, byte count,
SHA256, observation count, explicit missing-value dates and exclusions.

FRED VIX observations use a business-day calendar and can be revised. Weekends,
holidays and explicit missing values will not be filled. To guard against release
timing, a value will not be usable until the date of the second subsequent valid
FRED observation.
