# Independent NEWS_LONG PAPER worker

The shared `app_v8_fly` service runs the RSS refresh loop independently of FLY
and of dashboard requests. Existing RSS source validation, sentiment scoring,
two-hour headline lifetime and five-minute refresh interval are unchanged.

`news_paper` owns an independent simulated XRPUSDC portfolio in PostgreSQL
(`news_paper_state`, `news_paper_trades`). No exchange order API is used and no
additional Render service is required. The worker reuses the existing NEWS_LONG
market confirmation in read-only `news_only` mode, which cannot select a plain
breakout or an armed FLY entry. FLY, FAST and Lead-Lag remain paused.

One position at a time, risk 0.14% of the independent balance, max notional 35%,
net target 1.6R, fees and slippage inherited from FLY. ATR/min/max stop limits are
also inherited. Daily realized loss limit is 0.75% (UTC day), cooldown 30 minutes
after loss and 15 minutes after profit. News positions use their explicit SL/TP.
The stored position includes the entry headlines and execution-cost assumptions.

The quote/exit worker and market scanner are separate tasks, so unavailable RSS
or slow signal analysis does not stop price-based position management. Entries
require fresh news, fresh closed-candle analysis, a recent quote and limited
price drift. Headline and candle deduplication is persisted transactionally with
the position. Row locks protect against overlapping workers during deployment.

`/news-paper/status` and the NEWS LONG dashboard card expose the account, feed
freshness, waiting reason, errors, positions and closed trades. The status route
reads cached data only; viewing the page does not trigger news refresh.

Validation: `python -m unittest test_news_paper test_news_signal test_fly_entries`.
The regression fixtures verify execution behavior, not strategy profitability.
