# XRP_AGGRESSOR_SELL_BURST_REVERSAL_V1 — ingestion amendment

Recorded and committed before any performance result was produced.

The first full ingestion stopped at raw row 5,062,971 of the February 2026 monthly archive, before minute-bar construction completed or any backtest ran. The publisher CSV is not globally ordered: after aggregate-trade ID 688,808,344 at timestamp 1770769511118776 microseconds, it returns to ID 688,806,345 at the earlier timestamp 1770768000132951. A scan found two nonmonotonic boundaries in that archive. January and March–September 2026 were monotonic; all earlier archives had already streamed through the strict parser without error. The affected ZIP SHA256 is `cab6508d0123cee29a576af84794f1328e0093996cb93a56e7036e7c22ec9e9b` and its uncompressed CSV is 769,637,044 bytes.

Frozen ingestion-only correction: for this exact source hash, externally sort the complete CSV numerically by aggregate-trade ID before feeding it to the unchanged minute builder. Then require IDs to be strictly increasing and timestamps nondecreasing, count duplicates/discontinuities, and retain the same invalid-adjacent-minute/no-imputation rules. Record that one archive was reordered plus its raw disorder count in `results.json`. Do not sort or alter other archives. If the corrected stream still has duplicate IDs, reversed timestamps, or conflicting records, stop without performance evaluation.

This restores publisher event order; it does not change strategy parameters, signal thresholds, prices, sides, costs, folds, or acceptance gates. No return or trade outcome had been calculated when this amendment was written.
