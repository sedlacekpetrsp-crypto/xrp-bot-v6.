# RANGE_HARVEST_LIMIT_V1 preregistration — 2026-10-23

Use BTCUSDT spot only. From 20 completed daily bars calculate directional efficiency as absolute
net log return divided by summed absolute daily log returns, plus 20-day true-range ATR. When
efficiency is at most 0.35, place a resting buy limit for the next UTC day at prior close minus
0.50 ATR. Cancel if untouched after 24 hours. After fill, target the prior close, stop one ATR
below entry, or exit after 24 hours. Allocate 25% of equity; one position/order maximum.

Gap stops fill at the worse open. A stop touched on the fill bar wins; same-bar target is ignored
because the hourly high may precede the limit fill. Base execution charges 0.02% maker entry with
no entry slippage, then 0.095% taker exit plus 0.02% adverse exit slippage. Stress assumes 0.19%
taker fee and 0.04% adverse slippage on both sides. Incomplete days are removed, windows cannot
cross gaps, no candles are fabricated, and provenance hashes are stored.

Development is 2021 and 2022; both must be positive. Validation is 2023, 2024, 2025 and January–
September 2026. Pass gates: at least 150 trades, combined PF >=1.20 base and >=1.05 stress, every
block positive base, at least three stress-positive blocks, positive total stress, max drawdown
<=15%, and no positive block above 60% of positive P&L. Robust status additionally needs 50 new
forward PAPER trades. Failure retires V1 without changing regime, ATR, bracket or cost parameters.
