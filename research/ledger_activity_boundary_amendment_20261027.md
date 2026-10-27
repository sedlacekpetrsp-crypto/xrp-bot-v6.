# XRP_LEDGER_ACTIVITY_BREADTH_V1 — fold-boundary execution amendment

Recorded 2026-10-27 after a preliminary run exposed a mechanical omission and
before the final result is accepted or committed. If a position remains open when
a locked fold ends, it must be liquidated at the last complete in-fold close with
the same adverse slippage and exit fee, reason `END`. The preliminary runner
instead discarded that open position. This amendment prevents survivorship at
fold boundaries and matches the preregistered closed-trade evaluation intent.
Signal rules, costs, sizing, thresholds and acceptance gates are unchanged. The
entire backtest and independent audit must be rerun; only corrected outputs may
be retained.
