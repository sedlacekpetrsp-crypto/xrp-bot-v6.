# Autopilot STATE — přepisuje se každým během

Poslední aktualizace: 2026-11-05 10:15 UTC (autopilot běh #9 — zkušební, run 42007725592; produkce beze změny proti #8).

Plánovaná úloha „XRP BOT – Automatický vývoj a kontrola“ (cca à 3 h). Vypnout/změnit: claude.ai → plánované úlohy.

## Produkce (poslední známé hodnoty, 09:59 UTC)

- Služba `xrp-fly-whale-24-7` (`srv-dang770ae00c73em1sm0`), `uvicorn app_v8_fly:app`, větev `v8-fly-layer-test`.
  Podle zadání vlastníka je Auto Deploy ZAPNUTÝ (každý commit do větve = deploy); dnešní deploye byly
  všechny `trigger: manual` (vlastník). Do `v8-fly-layer-test` nic nepushovat bez schválení.
- **Nasazeno: `edaa938` (deploy `dep-dbm4i5ec6qcc73fve6tg`, live od 09:15:47 UTC) = HEAD `v8-fly-layer-test`,
  obsahuje `da2f665` (PR #5) i `9b41f6d` (PR #6).** `code_markers`: trendline 0,1 % = true, 3 % = false.
  Historie dnes: `bd55352` → `9b41f6d` (09:01) → `edaa938` (09:14, hned znovu 09:15:47).
- Endpointy 6× HTTP 200, vše healthy, `paused_bots` FAST/FLY/LEADLAG/TV, `persistence: postgres`.
- Render: žádné `server_failed`/restarty mimo deploye, error logy 0 (06:00–10:00), CPU ~0,03, RAM 158 MB / 512 MB.
- `WAIT postgres` (LH-WHALE, LIQUIDITY-LOCAL) beze změny formátu, level info ⇒ stále neškodné.
- P/L součet 14 PAPER účtů −3 180,67 (BEST-OF −383,00 / 129 obchodů; ostatní beze změny od 09:15).
- Combined: 0 pozic, 0 obchodů, `extra_rebalance_caused_by_pr5` false. ELITE V18/V56 0 obchodů.

## Databáze `xrp-bot-db` (1 GB, bez auto-zvětšení)

| UTC | Velikost | % z 1 GB | Top tabulky |
|---|---|---|---|
| 2026-11-05 09:59 | 201 MB | 19,6 % | research_market_samples 182 MB, blue_whale_state 3,9 MB, v8fixed_signals 1,7 MB |
| 2026-11-05 10:05 | 201 MB (210 646 719 B) | 19,6 % | beze změny pořadí |

Trend: research_market_samples ~1 438 vzorků/den, ~6,9 kB/vzorek ⇒ ~9,7 MB/den (jediný významný růst).
Odhad: 85 % ≈ 2027-01-13 (~69 dní), 100 % ≈ 2027-01-29 (~85 dní). Zatím bez varování.
Návrh na později (jen se souhlasem): export starších `research_market_samples` (payload bytea) do
souborů/artefaktů a archivace, nebo zvětšení disku. Nic se nemaže.

## Anomálie (nová) — BEST-OF duplicitní uzavření

- `bestof_trades` id 128 a 129: stejná pozice XRPUSDT BREAKOUT LONG (opened 08:20:29), zavřena 09:14:07
  a 09:14:10 — při ručních deployích běžely krátce dvě instance (stará + nová) a obě ji uzavřely.
- `paper_balance` 9 617,00 je správně (odečteno 1×, −383,00); tabulka obchodů/počet a statistiky 2×
  (129 obchodů, součet pnl −393,31). Stejná třída chyby jako dřív u FLY (`fly_trade_exclusions`).
- Oprava: **draft PR #8** (`research/bestof-dedupe-20261105`, `418f897`): idempotentní `save_trade`
  (advisory lock + kontrola symbol+setup+opened_at) + test. Data se nemění; případná korekce id 129
  (např. tabulka výjimek jako u FLY) jen se souhlasem vlastníka.
- Riziko trvá u každého deploye: i ostatní boty bez ochrany mohou zapsat duplikát při překryvu instancí.

## Otevřené úkoly (priorita shora)

1. PR #8 čeká na review/schválení vlastníka (merge = deploy). Po nasazení ověřit, že při dalším
   deployi nevznikne duplikát. Zvážit obecnější ochranu (leader lock pro celý obchodní loop, ostatní boty).
2. Kontrola duplicit při každém běhu (SELECT na `*_trades` group by opened_at) — přidat do workflow/RUNBOOK.
3. Combined replay: export ledgeru HOTOVO (draft PR #9 → research/autopilot, `research/combined_selection_replay/trades/`,
   CONSISTENT, 300 legů). Dál: 1. 12. 2026 spustit NOVÝ běh s `--end 2026-12-01` (stejný protokol + export),
   výsledky přidat jako nový řádek, předchozí nepřepisovat.
4. Forward PAPER evidence: týdně souhrn ELITE V18/V56, Combined, LH-WHALE, LIQUIDITY, Swing
   (počet, P/L, PF); ≥ 30 nových obchodů na strategii před závěrem. Registr: `automation/STRATEGY_REGISTRY.md`.
5. `test_expired_and_future_signals_never_open` prochází jen formálně — přepsat v PR.
6. `render.yaml` neodpovídá službě (`app_v8_ui` vs `app_v8_fly`) — opravit v PR.

## Čeká na vlastníka

- Draft PR #8 (BEST-OF duplicitní zápis) — schválit/zamítnout; rozhodnout o korekci řádku id 129.
- Draft PR #9 (Combined ledger export, cíl research/autopilot) — review; produkce se nemění.

## Blokace

- Žádné. Render konektor funguje (čtení). Sandbox nemá PyPI ⇒ testy s FastAPI běží v GitHub Actions
  (lokálně jen se stuby).
