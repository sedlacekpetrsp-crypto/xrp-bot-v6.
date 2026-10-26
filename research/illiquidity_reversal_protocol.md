# XRP_ILLIQUIDITY_SHOCK_REVERSAL_V1 — frozen protocol

Status: preregistered before historical performance evaluation on 2026-10-26. No profitability claim.

## Distinct hypothesis

An unusually large negative hourly log return per USDT of reported spot quote volume is an Amihud-style temporary-liquidity shock. XRP may partially reverse after liquidity normalises. This tests price impact per quote-dollar, not taker imbalance, trade size, cross-market relative returns, serial correlation, calendar drift, derivatives positioning or premium.

## Fixed signal and execution

- Market/data: Binance spot XRPUSDT monthly 1h klines, January 2022 through September 2026. Preserve reported quote-asset volume; never infer or fill it.
- At each closed hour `i`, compute `impact=max(0,-log(close_i/close_{i-1}))/quote_volume_i`.
- Require the current log return <= -1.0% and current impact >= the linearly interpolated 97.5th percentile of the preceding 720 impacts, excluding the current bar. The entire 721-hour return/volume history must be consecutive and every quote volume positive.
- Enter spot LONG at the next hourly open with 2 bps adverse slippage. One position only.
- Causal 24-hour ATR, stop 1.5 ATR, target 2.0R, maximum 12 bars. A gap through the stop fills at the worse open; if stop and target occur in one candle, stop wins.
- Risk 0.5% of current equity to the initial stop, capped at 20% notional, no leverage. Fee 9.5 bps per side. Stress doubles fee and slippage.

## Frozen validation and gates

Treat 2022 as control. Evaluate locked quarterly folds from 2023Q1 through 2026Q3, starting each flat with $10,000; also report continuous OOS drawdown. Do not tune after viewing results. Store archive URLs, byte counts and locally calculated SHA256, gaps, ledgers, code tests and an independent arithmetic audit.

All historical gates must pass: at least 150 quarterly OOS trades; base net and expectancy positive with PF >1.15; stressed net and expectancy positive with PF >1.02; at least 10 of 15 quarters positive and 2026Q3 positive; continuous base and stress drawdown <=10%; no quarter contributes more than 30% of total positive-quarter profit. Even then the status remains TEST NEDOKONČEN until at least 30 future calendar days and 100 newly timestamped non-overlapping forward PAPER trades have positive stressed expectancy. Historical success alone can never mean PROŠEL.

