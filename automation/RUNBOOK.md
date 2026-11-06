# Autopilot runbook — xrp-bot-v6 (PAPER only)

Tento dokument řídí každý automatický běh. Platí pro Claude i pro další vývojáře.

## Nepřekročitelná pravidla

1. Výhradně PAPER. Nikdy LIVE, žádné API klíče burzy, žádné příkazy na burzu.
2. Žádný merge, push ani PR merge do `v8-fly-layer-test` (spouští Render deploy) ani do `main`
   bez výslovného souhlasu vlastníka v chatu. Draft PR je povolen, merge ne.
3. Žádné změny produkčního ledgeru/DB. Produkce se čte jen veřejnými GET endpointy.
4. Žádné tajné hodnoty v repozitáři, logu ani reportu.
5. Strategie není „zisková“ bez nezávislé validace po nákladech (fee + skluz/spread, stres 2×/3×,
   chronologicky oddělená data nepoužitá při ladění, ≥ 30 nových obchodů).
6. Protokol, parametry a brány zapsat a commitnout PŘED prvním výsledkem; po výsledku neladit.
7. Pracovní větev: `research/autopilot`. Ostatní větve jen číst.

## Postup jednoho běhu (cca 3 h interval)

1. `git fetch` a `git checkout research/autopilot && git pull`. Přečíst `automation/STATE.md`.
2. Zapsat aktuální UTC čas do `automation/RUN_REQUEST`, commit + push → spustí
   `.github/workflows/autopilot-checks.yml` (status snapshot + celá testovací sada).
3. Počkat na doběhnutí (GitHub MCP `actions_list` / `get_job_logs`), z logu vzít řádky
   `AUTOPILOT_SUMMARY {...}` a `AUTOPILOT_TESTS ...`.
4. Vyhodnotit proti minulému stavu v `STATE.md`:
   - HTTP ≠ 200, `healthy=false`, `error`/`last_error`, změna `paused_bots`, restart procesu
     (`process_started_utc`), nečekaná změna počtu obchodů nebo P/L, `extra_rebalance_caused_by_pr5`.
   - Nový deploy: změna `process_started_utc` ⇒ zjistit, zda běží `da2f665`.
   - Duplicitní zápisy obchodů: spustit `tools/autopilot/duplicate_trades_check.sql` přes Render
     `query_render_postgres` (jen SELECT). Známý stav: bestof_trades 1 skupina (id 128/129). Jakékoli
     zvýšení `dup_groups` = anomálie → nahlásit vlastníkovi.
5. Zapsat výsledek do `automation/TEST_LOG.md` (1 řádek/běh) a aktualizovat `STATE.md`
   (poslední hodnoty, otevřené úkoly, blokace). Commit + push (bez změny RUN_REQUEST).
6. Pokračovat v nejvyšší otevřené položce backlogu v `STATE.md`, pokud se vejde do běhu.
   Kód + testy → draft PR do `v8-fly-layer-test` s reprodukovatelnými výsledky, nikdy merge.
7. Při anomálii (výpadek, chyba, nečekaný obchod, ztráta persistence) napsat stručně vlastníkovi.
8. Přečíst `automation/DIALOG.md` (spolupráce s ChatGPT, od 2026-11-06). Je-li vložena nová odpověď ChatGPT:
   zpracovat ji (oponentury ověřit výpočtem/testem, hypotézy převést do `IDEAS.md` a posoudit podle rámce v2),
   do DIALOG.md zapsat „Odpověď Clauda (kolo N)“ a „Kolo N+1 — otázky Clauda“ (max. 5 konkrétních otázek),
   1 řádek do reportu. Shoda asistentů není důkaz; platí jen test po nákladech a forward PAPER.

## Co lze a nelze (stav 2026-11-05)

| Potřeba | Cesta | Stav |
|---|---|---|
| Kód, PR, Actions | GitHub MCP v session | funguje |
| Tržní data (Binance Vision) | GitHub Actions runner | funguje |
| Stavové endpointy služby | GitHub Actions runner (GET) | funguje |
| Render deploye/události/logy/metriky | Render konektor (jen čtení, workspaceId `tea-daar0pcs728c73fjrhkg`) | funguje (od 2026-11-05 10:00 UTC) |
| PostgreSQL přímo | Render `query_render_postgres` (jen SELECT) | funguje |
| Síť ze session | — | blokována pro Render/Binance (zamítnuto rozšíření prostředí) |
