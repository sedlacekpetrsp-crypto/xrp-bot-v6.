# XRP_ATTENTION_SHARE_SURGE_V1 — frozen protocol

Status: preregistered before performance evaluation on 2026-10-26. No profitability claim.

An unusually high share of XRP in total reported spot USDT quote volume of a fixed basket (BTC, ETH, BNB, SOL, XRP) measures XRP-specific market attention. Elevated attention may persist into the next UTC day. This is not relative price strength, breadth, taker imbalance, trade size, price impact, OI, funding, premium, volatility, serial dependence or order-book depth.

- Real Binance Vision spot 1h klines, January 2022–September 2026; use reported quote-asset volume. Fixed basket: BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT.
- At each 23:00 UTC close, sum quote volume over exactly 24 consecutive closed hours. XRP attention share is XRP volume divided by basket volume.
- Signal only when current share is strictly above the interpolated 80th percentile of the preceding 180 complete daily shares, excluding current. All 181 days must be consecutive and aligned across every market. No imputation.
- Enter XRP spot LONG at the following 00:00 open. Stop 3% below slipped entry, target 6% above entry, maximum hold 24 hours. Gap stop fills at worse open; ambiguous bar uses stop first.
- Fee 9.5 bps/side, adverse slippage 2 bps/side; stress doubles both. Risk 0.5% of equity to stop, capped at 20% notional, no leverage, one position, no overlap.

Validation: 2022 control; annual OOS folds 2023–2026 (2026 through September), each flat at $10,000, plus continuous OOS. Preserve URLs, SHA256, gaps, ledgers and independent audit. No retuning. All historical gates: >=100 OOS trades; positive net/expectancy and PF>1.15 base; positive net/expectancy and PF>1.02 stressed; >=3/4 profitable folds including 2026; continuous base/stress drawdown <=10%; no month >40% of positive aggregate profit. Historical passage still means TEST NEDOKONČEN until >=30 future days and >=100 new forward PAPER trades show positive stressed expectancy.

