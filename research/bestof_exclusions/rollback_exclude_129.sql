-- Návrat: zruší vyloučení id 129. Řádek v bestof_trades nikdy nezmizel, takže po restartu
-- (load_state) je historie i statistika přesně jako před opravou.
BEGIN;
DELETE FROM bestof_trade_exclusions WHERE trade_id = 129;
COMMIT;
