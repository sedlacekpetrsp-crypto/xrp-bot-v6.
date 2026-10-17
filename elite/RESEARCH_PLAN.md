# ELITE Research V1 — isolated research branch

Status: RESEARCH ONLY. No live or paper execution wired. No deployment.

## Hypothesis
XRP/USDT short-horizon returns may have regime-dependent mean-reversion following statistically unusual moves. This must be falsified on out-of-sample data. Do not reuse BEST breakout/pullback or Hunter sweep/reclaim triggers.

## Candidate signal
- Use only fully closed 5-minute candles.
- Estimate rolling log-return z-score with a trailing window, excluding the current bar from its baseline.
- Detect volatility regime using trailing realized volatility percentile.
- In range/normal-volatility regime, evaluate contrarian entries after extreme standardized returns; skip strong-trend/high-volatility regimes.
- Entry no earlier than next bar; do not use future observations for filters.
- Exit via volatility-scaled stop and target, with time-based exit treated as an experimentally tested parameter, not a default assumption.

## Evaluation
- At least 12 months historical XRPUSDT candles, data quality checks, chronological walk-forward train/validation/test splits.
- Include trading fees, slippage, spread, adverse fill assumptions and position constraints.
- Compare net expectancy, profit factor, drawdown, trade count, Sharpe with uncertainty intervals, and overlap of entry timestamps with BEST/Fly/Hunter.
- Stress test fee x2, slippage x2 and market regimes; reject if edge disappears out of sample.
- Never optimize on held-out test periods. Avoid look-ahead and survivorship biases.

## Risk
- Research starting risk cap: 0.5% of paper equity per trade, maximum one concurrent position.
- Portfolio-level cap needed before any real-money use. Stops are not guaranteed during gaps or outages.
- PAPER only after tests pass and separate approval. Live trading requires separate explicit approval.

## Acceptance
Do not claim profitable until independently verified, statistically credible out-of-sample results. Do not deploy or modify existing services.
