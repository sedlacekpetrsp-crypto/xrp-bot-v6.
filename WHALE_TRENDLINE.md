# Blue Whale: XRP 4h trendline PAPER addition (2026-10-07)

Adds the previously tested 4h LONG support-bounce rule to the existing Whale
worker and Postgres state. Original FIB/VWAP positions and history are preserved.
No new service, subscription, exchange credentials, or real orders.

Source: Trendline-XRP-pulrocni-test-2026-10-06.md. The original half-year
simulation had 15 trades, 53.33% wins, +72.37 USDT from 10,000, +57.43 at
double costs, **at 0.1% target risk and 35% maximum notional**. It is an
exploratory small-sample result, not an independent validation or a forecast.
Aroon and Supertrend are already in swing_paper.py; this trendline rule was not.

User subsequently requested **3% risk**. This implementation targets 3% of the
Whale account including modeled costs, bounded by available cash including
entry fees, without leverage. Actual risk can therefore be lower. Other Whale
strategies keep their existing limits. Shared per-entry coordinator recognizes
WHALE_TRENDLINE explicitly; mixed Whale positions have a maximum initial risk
budget of 3.12%, versus the original 0.24% when no trendline is involved.
These sizing changes mean the old backtest return is not the return of this
configuration and must not be linearly scaled or shown as live performance.

Rules: strict pivots with three completed candles on each side, two rising
support anchors 5–80 candles apart, latest anchor no older than 120 candles,
no intervening close below support minus 0.25 ATR14. Bounce low within 0.2 ATR,
bullish close over support +0.15 ATR, prior close above support. Fixed stop
2 ATR from signal close; target 2R from actual entry; stop range 0.2–12%.
No extra MTF/news filter, trailing, breakeven or time exit for this rule.
One position per asset and two Whale positions total still apply. A setup is
consumed even if blocked by available capital, an existing position or cooldown.

Forward execution uses current observed public quotes, not retrospectively
filled historical bar opens. Signals expire five minutes after the 4h close,
entries retain the existing 0.35% price-deviation guard. SL/TP are checked by
the existing quote loop (~10s plus request latency); this can miss intrabar
excursions unlike the historical 5m OHLC backtest. Stop gaps can exceed the
planned loss. A 60-minute strategy cooldown applies after close. Anchor IDs
and evaluated candle timestamps persist over restart. DB failure blocks entries.

Dashboard: total statistics before coin diagnostics, separate trendline count,
win rate and realized net P/L, dash instead of zero for no trendline trades.
No historical results were imported into the live PAPER history.

Validation: 8 new tests cover support recognition, broken/unconfirmed pivots,
3% sizing including costs, cash cap, legacy preservation, persisted dedup,
stale/DB blocking, and disabling time exit/breakeven. Existing exit regressions
pass. Three legacy Telegram scanner tests already fail on the unchanged parent
commit ef115bf, because the current scanner no longer consumes Telegram posts;
verified on an isolated baseline, not introduced by this change.
