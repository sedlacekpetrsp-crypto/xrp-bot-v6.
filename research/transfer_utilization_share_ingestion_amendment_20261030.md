# XRP_TRANSFER_UTILIZATION_SHARE_V1 — pre-result genesis-row amendment

The first complete ingestion stopped before calculating any signal, trade or performance because the CoinMetrics response contains one genesis-era row at 2013-01-01 with `TxCnt=0` and `TxTfrCnt=136`, making the preregistered ratio undefined. All later rows pass the fixed finite, positive-denominator checks.

Before rerunning, restrict metric ingestion to timestamps on or after 2019-01-01. This predates the first 2020 control entry by a full year and exceeds the frozen 180-day warm-up; it changes no eligible test observation. Preserve and hash the full raw response, report the one excluded pre-window row, and continue to require the retained calendar to be exactly consecutive. Do not replace, divide, interpolate or carry the invalid row. Signal, threshold, lag, execution and acceptance gates remain unchanged.
