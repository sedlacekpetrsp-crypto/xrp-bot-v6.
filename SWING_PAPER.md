# Independent forward PAPER accounts

Aroon 1h LONG with last completed 4h EMA20>EMA50 and close>EMA200 filter; Supertrend 4h LONG/SHORT. Entry/exit definitions match the previously researched simple ATR14 variants. Each account starts with 10,000 virtual USDT, risk target 0.5%, initial aggregate risk budget 1.5%, 35% per-position/70% combined notional cap, maximum two positions. Symbol priority XRP/BTC/ETH/SOL. Best and all existing balances/risk coordinators are unchanged.

Only public market data is used. There are no order or private exchange endpoints. Trades cannot be executed with real funds. `/swing/status` exposes account health, positions, signal checks, and history; the main dashboard adds two cards.

Persistence: `swing_paper_accounts` holds one JSON state per strategy, including cash, positions, consumed signals, cooldowns, drawdown, lifetime counters and last 500 trades. `swing_paper_trades` is the permanent, unbounded trade ledger keyed by strategy/symbol/signal time. Account row locking and atomic state/ledger transactions prevent restart duplication and partial closes. Missing DB or failed writes do not create an in-memory trading fallback. SQL uses a connection/statement/lock timeout. These additive tables are created by the app at startup.

Initial startup consumes old signals; entries require a new candle after account activation and at most 120 seconds old. Later restarts keep the activation timestamp and consumed signals. Price quotes over 15 seconds old cannot execute. Indicator failures still allow price-based stops. Outages cannot guarantee stops or fills; no retrospective fill is invented. The loop normally polls every five seconds; bounded data retrieval can delay it. Exits use live observed prices with modeled slippage, so forward results will differ from 15m OHLC simulation.

Fees 0.095% per side, slippage 0.02% per side. Hypothetical SHORT carry 0.01%/8h prorated. Initial SL 2.5 simple ATR14, trailing 3 ATR at completed native closes, signal exits; cooldown 20m loss, 5m otherwise. Indicator warmup uses up to 1,000 available native candles, so recursive indicator initialization can differ slightly from long-history research. Drawdown is observed account equity, not an intratick bound.

Validation: `python -m unittest -v test_swing_paper test_bestof_ema4h test_bestof_ema4h_persistence`. Research parity independently checked on historical OHLC for both native strategies and completed-candle filter. Dashboard generated and JavaScript parsed before deployment.

Rollback: revert the deployment commit or remove the two imports, dashboard enhancement, and install call. Retain additive DB tables and ledger; do not reset accounts on deploy.
