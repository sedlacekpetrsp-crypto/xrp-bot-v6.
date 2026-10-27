# Top-of-book source feasibility check — 2026-10-27

The planned three-leg XRPUSDT/XRPBTC/BTCUSDT spot triangular-dislocation study requires synchronized executable spot bids and asks. The official Binance Vision spot path `data/spot/daily/bookTicker/XRPUSDT/...` returned HTTP 404 for a representative date. Futures top-of-book archives exist for historical XRPUSDT USD-M and XRPUSD_PERP COIN-M contracts, but do not supply the required XRPBTC spot leg.

Representative 2024-01-01 futures archives were also operationally large: the XRPUSDT USD-M ZIP was 33,550,718 bytes (216,259,254-byte CSV) and the inverse XRPUSD_PERP ZIP was 6,223,930 bytes (42,880,143-byte CSV) for one day. Using candle closes instead of synchronized spot bid/ask would fabricate executability and understate spread/latency risk.

Decision before any performance evaluation: do not register or score triangular arbitrage from candle proxies. Preserve this as a data-feasibility result, not a failed trading strategy. Proceed to a separately frozen tick-sequence hypothesis using actual spot aggregate trades, whose official daily and monthly archives were confirmed available. No return was inspected during this source check.

