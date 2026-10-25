# MULTI_STABLE_PEG_REVERSION_V1 — frozen protocol (2026-10-25)

Status: **REGISTERED; NOT EVALUATED.** This tests stablecoin redemption-anchor reversion, not directional crypto momentum, flow, volume, funding, basis, calendar, cross-asset or volatility signals.

Markets: Binance spot USDCUSDT, FDUSDUSDT, TUSDUSDT, 15m, Jan 2024–Sep 2026. A symbol signals after a closed candle at or below 0.9940 USDT. Enter long at the next open only if that raw open is <=0.9960. Fixed target 0.9990, stop 0.9880, maximum 672 candles (7 days). Stop wins same-candle ambiguity; gap stop fills at worse open. One position per symbol; each symbol has an isolated one-third capital sleeve, current-equity risk <=0.5% and notional <=20% of its sleeve. Thus simultaneous positions remain <=20% total initial portfolio gross. No leverage or cross-sleeve reallocation.

Fees 9.5 bps and adverse slippage 2 bps per side; stress doubles both. Actual monthly archives, exact URLs and SHA256. Every candle timestamp, OHLC and monthly coverage must be complete; no imputation. 2024 is descriptive control. Locked OOS quarters: 2025 Q1–Q4 and 2026 Q1–Q3. Segment begins flat and liquidates at the end; continuous 2025–Sep 2026 is a non-independent reconciliation.

All gates required: >=90 aggregate symbol-quarter OOS trades; aggregate base net/expectancy positive and PF>1.15; stress net/expectancy positive and PF>1.02; every symbol positive at base and stress; >=5/7 quarters positive at base including 2026 Q3; continuous base/stress portfolio drawdown <=10%; no symbol or quarter >50% of positive profit. Even then, status remains `TEST NEDOKONCEN` pending >=30 future days and >=100 independent forward PAPER trades with positive stressed expectancy. No tuning after results; no LIVE, Render, main, production or deployed-branch changes.

Next: commit protocol, simulator, archive runner and mechanics tests; then evaluate unchanged rules.
