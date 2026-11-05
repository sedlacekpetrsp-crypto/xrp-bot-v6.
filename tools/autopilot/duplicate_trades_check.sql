-- Autopilot: kontrola duplicitních zápisů obchodů (JEN SELECT, read-only).
-- Spouštět každým během přes Render query_render_postgres. Výsledek = počet skupin se stejnou
-- pozicí (symbol + side + opened_at [+ setup/strategy]) zapsanou víckrát.
-- Známý stav 2026-11-05: bestof 1 (id 128/129, čeká na PR #10); FLY duplikáty už vyloučeny ve fly_trade_exclusions.
SELECT 'bestof_trades' AS tbl, (SELECT count(*) FROM bestof_trades) AS n, count(*) AS dup_groups
  FROM (SELECT 1 FROM bestof_trades GROUP BY symbol, side, setup, opened_at HAVING count(*) > 1) d
UNION ALL SELECT 'fast_scalp_trades', (SELECT count(*) FROM fast_scalp_trades), count(*)
  FROM (SELECT 1 FROM fast_scalp_trades GROUP BY symbol, side, opened_at HAVING count(*) > 1) d
UNION ALL SELECT 'tv_consensus_trades', (SELECT count(*) FROM tv_consensus_trades), count(*)
  FROM (SELECT 1 FROM tv_consensus_trades GROUP BY symbol, side, opened_at HAVING count(*) > 1) d
UNION ALL SELECT 'leadlag_trades', (SELECT count(*) FROM leadlag_trades), count(*)
  FROM (SELECT 1 FROM leadlag_trades GROUP BY side, opened_at HAVING count(*) > 1) d
UNION ALL SELECT 'blue_whale_trades', (SELECT count(*) FROM blue_whale_trades), count(*)
  FROM (SELECT 1 FROM blue_whale_trades GROUP BY signal_id, side, opened_at HAVING count(*) > 1) d
UNION ALL SELECT 'lh_whale_trades', (SELECT count(*) FROM lh_whale_trades), count(*)
  FROM (SELECT 1 FROM lh_whale_trades GROUP BY trade->>'symbol', trade->>'side', trade->>'setup', trade->>'opened_at' HAVING count(*) > 1) d
UNION ALL SELECT 'liquidity_v2_trades', (SELECT count(*) FROM liquidity_v2_trades), count(*)
  FROM (SELECT 1 FROM liquidity_v2_trades GROUP BY trade->>'symbol', trade->>'side', trade->>'setup', trade->>'opened_at' HAVING count(*) > 1) d
UNION ALL SELECT 'news_paper_trades', (SELECT count(*) FROM news_paper_trades), count(*)
  FROM (SELECT 1 FROM news_paper_trades GROUP BY trade->>'symbol', trade->>'side', trade->>'setup', trade->>'opened_at' HAVING count(*) > 1) d
UNION ALL SELECT 'swing_paper_trades', (SELECT count(*) FROM swing_paper_trades), count(*)
  FROM (SELECT 1 FROM swing_paper_trades GROUP BY strategy, trade->>'symbol', trade->>'side', trade->>'opened_at' HAVING count(*) > 1) d
ORDER BY 1;
