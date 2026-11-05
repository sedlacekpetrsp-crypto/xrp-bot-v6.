-- NÁVRH, NEPROVEDENO. Spustit jen s výslovným souhlasem vlastníka, až po nasazení kódu,
-- který tabulku bestof_trade_exclusions vytvoří a čte (init_db / load_state).
-- Vyloučí duplicitní zápis id 129 (2. zápis uzavření pozice id 128). Nic nemaže ani nemění
-- v bestof_trades ani ve stavu. Pojistka: zapíše se jen, pokud 128 a 129 jsou skutečně
-- totéž otevření (symbol + setup + opened_at + ceny + qty) a 129 je pozdější zápis.
BEGIN;
INSERT INTO bestof_trade_exclusions (trade_id, canonical_trade_id, reason)
SELECT d.id, c.id,
       'Duplicate close of opening 2026-11-05 08:20:29 UTC written by old instance during overlapping deploy 09:14 UTC'
FROM bestof_trades c
JOIN bestof_trades d
  ON d.id = 129 AND c.id = 128
 AND d.symbol = c.symbol AND d.setup IS NOT DISTINCT FROM c.setup
 AND d.opened_at = c.opened_at AND d.closed_at > c.closed_at
 AND d.entry_price = c.entry_price AND d.exit_price = c.exit_price AND d.qty = c.qty
ON CONFLICT (trade_id) DO NOTHING;
-- Kontrola před COMMIT: musí vrátit přesně 1 řádek (129 -> 128).
SELECT trade_id, canonical_trade_id FROM bestof_trade_exclusions WHERE trade_id = 129;
COMMIT;
