# Autopilot STATE — přepisuje se každým během

Poslední aktualizace: 2026-11-06 01:15 UTC (autopilot běh #17, run 42141322229; produkce beze změny; výzkum: ETHBTC switch zamítnut, PR #17; fronta +3 hypotézy, protokol #8 commitnut).

Plánovaná úloha „XRP BOT – Automatický vývoj a kontrola“ (cca à 3 h). Vypnout/změnit: claude.ai → plánované úlohy.

## Produkce (poslední známé hodnoty, 13:06 UTC — beze změny od 09:59 kromě níže uvedeného)

- 13:06: live `edaa938` = HEAD `v8-fly-layer-test`, obsahuje `da2f665`; žádné události od 10:00; error logy 0 (10:00–13:06);
  proces od 09:15:38; 6× HTTP 200, vše healthy, paused FAST/FLY/LEADLAG/TV; P/L −3 180,67 (beze změny);
  tests 238 passed; CPU ~0,03, RAM 164–168 MB / 512 MB; `WAIT postgres` stále level info, stejný formát.


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

Poslední kontrola 2026-11-06 01:04 UTC: 217,3 MB = 20,2 % (+0,8 MB za 2 h); produkce 01:04 beze změny (live edaa938 = HEAD, 0 událostí od 23:00, 0 error logů, dup jen id 129, BEST-OF 131, P/L −3 176,32, testy OK). Předchozí 23:03: 216,5 MB = 20,2 % (+0,9 MB za 2 h, trend beze změny); produkce 23:03 beze změny (live edaa938, 0 událostí od 21:00, 0 error logů, dup jen id 129, BEST-OF 131, P/L −3 166,91). Předchozí 21:03: 215,6 MB = 20,1 %. Produkce 21:03 beze změny (live edaa938, 0 událostí od 19:00, 0 error logů, dup jen id 129, BEST-OF 131, P/L −3 166,91, 238 passed). Předchozí 19:04: beze změny (live edaa938 = HEAD, obsahuje da2f665, 0 událostí od 17:00, 0 error logů 17:05–19:05, BEST-OF 131 obchodů, dup_groups jen známý id 129, P/L součet −3 197,26, tests OK).

| UTC | Velikost | % z 1 GB | Top tabulky |
|---|---|---|---|
| 2026-11-05 09:59 | 201 MB | 19,6 % | research_market_samples 182 MB, blue_whale_state 3,9 MB, v8fixed_signals 1,7 MB |
| 2026-11-05 10:05 | 201 MB (210 646 719 B) | 19,6 % | beze změny pořadí |
| 2026-11-05 13:06 | 202 MB (212 006 591 B) | 19,7 % | research_market_samples 184 MB, blue_whale_state 4,0 MB, v8fixed_signals 1,7 MB, v8_signals 0,4 MB, tv_consensus_state 0,3 MB |

Trend: research_market_samples ~1 438 vzorků/den, ~6,9 kB/vzorek ⇒ ~9,7 MB/den (jediný významný růst).
Měřeno 10:05→13:06: +1,36 MB / 3 h ≈ 10,8 MB/den (krátké okno, konzistentní s ~10 MB/den).
Odhad: 85 % ≈ 2027-01-09 až 01-13 (~65–69 dní), 100 % ≈ 2027-01-24 až 01-29. Zatím bez varování.
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
- Regresní test proti skutečnému PostgreSQL (`139d8b5`, `test_bestof_dedupe_postgres.py` + workflow
  `bestof-dedupe-postgres.yml`): opakované zpracování i 8 souběžných instancí ⇒ 1 řádek; bez zámku duplikát
  vznikne (síla testu); zámek drží celou transakci; chyba uvnitř = žádný řádek, zámek uvolněn. Bez opravy
  (`edaa938`) test selže. CI run 42008665479: 23 passed + 5× 6 passed. Riziko: samotný deploy opravy může
  ještě jednou zdvojit zápis (stará instance bez zámku) ⇒ nasadit bez otevřené BEST-OF pozice.
- Riziko trvá u každého deploye: i ostatní boty bez ochrany mohou zapsat duplikát při překryvu instancí.

## VÝZKUMNÁ FRONTA STRATEGIÍ — PRIORITA Č. 1 (vlastník 2026-11-05 14:31: „soustřeď se“)

Každý běh: kontroly produkce co nejkratší (jen odchylky), pak **jedna hypotéza z této fronty** od
začátku do konce. Hotovou položku označ výsledkem a odkazem, pak pokračuj další. Všech 110 dřívějších
hypotéz je v `reports/hypothesis-inventory-20261105.md` (103 NEPROŠLO) — nic z toho neopakovat.

Společný protokol (zapsat do `research/<název>/PROTOCOL.md` a commitnout PŘED prvním výsledkem):
- data: Binance Vision spot 1d/1h klines (veřejná, bez klíčů), SHA-256 archivů do `data_source.json`;
  relace sama na data.binance.vision nedosáhne ⇒ stahování a backtest spouštět přes GitHub Actions
  (vzor `.github/workflows/combined-trade-ledger.yml`), výsledky commitnout zpět; lokálně jen logiku a testy.
- náklady: poplatek 0,095 % + skluz 0,02 % na stranu, citlivost ×1 / ×2 / ×3;
- dělení: ladění 2020-09…2022-12, validace 2023-01…2024-12, závěrečný test 2025-01…2026-10
  použít JEDNOU, nic podle něj neladit; parametry max. malá předem daná mřížka;
- měřítko: musí porazit buy & hold téhož aktiva rizikově (Sharpe, max DD) a mít ≥ 30 obchodů ve validaci;
  kladný výsledek bez 3 nejlepších obchodů; PF > 1,2 po nákladech ×2;
- výstup: `trades.csv` (každý obchod), `results.json`, `RESULTS.md`, řádek ve `STRATEGY_REGISTRY.md`,
  draft PR do `research/autopilot`. Výsledek „prošlo“ = jen kandidát na forward PAPER, ne „zisková“.

Fronta:
1. ~~Donchian trend 20/55~~ — HOTOVO 2026-11-05 14:00 UTC: **ZAMÍTNUTO** (validace Sharpe 1,35 < B&H 1,94; závěrečný test −21 % po nákladech ×2). PR #11, `research/donchian_trend/RESULTS.md`.
2. ~~Turn-of-month BTC/ETH~~ — HOTOVO 2026-11-05 15:10 UTC: **ZAMÍTNUTO** (ladění +242 %, ale validace −32,6 % vs B&H +321 %, placebo ToM nejhorší z 28 oken; závěrečný ×2 −16,7 %). PR #12, `research/turn_of_month/RESULTS.md`.
   Poučení: kalendářní efekt z 2020–22 se mimo vzorek obrátil ⇒ jednoduché anomálie z ladicího období nepřenášet.
3. ~~RSI(2) pullback v uptrendu BTC/ETH~~ — HOTOVO 2026-11-05 17:20 UTC: **ZAMÍTNUTO** (krit. 1: validace +21 %, Sharpe 0,59 vs B&H +321 %, 1,71; ostatní 4 kritéria splněna; ladění −0,5 %; závěrečný ×2 +11,5 % vs B&H −25 %, DD 6 %). PR #13, `research/rsi2_pullback/RESULTS.md`.
   Poučení: nízká expozice (~4 dny/obchod) v býčím trhu nemůže porazit B&H na Sharpe; nápad na budoucí hypotézu = kombinace s B&H/overlay (nový protokol, ne ladění podle závěrečného testu).
4. ~~SMA200 risk-off overlay BTC/ETH~~ — HOTOVO 2026-11-05 19:20 UTC: **ZAMÍTNUTO** (krit. 1, 2, 5: validace +187 %, Sharpe 1,43, 14 obch. vs B&H +321 %, 1,71; závěrečný ×2 −7,2 % vs B&H −25 %, DD 30 vs 60 %). PR #14, `research/sma200_overlay/RESULTS.md`.
   Poučení: overlay ~půlí drawdown, ale v býčím období ztrácí Sharpe a mění stav zřídka (< 30 obchodů) ⇒ režimové filtry na B&H podle těchto kritérií neprojdou; další hypotézy s vyšší frekvencí.
5. ~~Denní volatilitní průraz k=0,5 BTC/ETH~~ — HOTOVO 2026-11-05 21:10 UTC: **ZAMÍTNUTO** (krit. 1, 3, 5: validace ×1 +58,8 %, Sharpe 1,02, 607 obch. vs B&H +321 %, 1,71; validace ×2 −21 %, PF 0,91; závěrečný ×2 −66 % vs B&H −25 %). PR #15, `research/vol_breakout/RESULTS.md`.
   Poučení: hrubá hrana ~40 bps/obchod při ~23 bps nákladů na kolo ⇒ vysokofrekvenční denní obchodování spot s 0,095% poplatkem nepřežije stres ×2; další hypotézy s nízkým obratem.
6. ~~Hlasování časového momenta 1/3/6/12 m BTC/ETH~~ — HOTOVO 2026-11-05 23:10 UTC: **ZAMÍTNUTO** (krit. 1, 5: validace ×1 +108 %, Sharpe 1,14, DD 32,4 %, 34 obch. vs B&H +321 %, 1,71, 34,0 %; závěrečný ×2 −22,0 % vs B&H −25,1 %, DD 33 vs 60 %). PR #16, `research/ts_momentum_vote/RESULTS.md`.
   Poučení: stejný vzor jako SMA200 (PR #14) — časování trhu půlí DD v medvědím trhu, ale v býčím ztrácí Sharpe; info: týdenní varianta Sharpe 1,44 (pořád < 1,71). Časování trhu proti B&H dál netestovat.
7. ~~Přepínání BTC ↔ ETH podle ETHBTC SMA50~~ — HOTOVO 2026-11-06 01:10 UTC: **ZAMÍTNUTO** (krit. 1, 5: validace ×1 +184 %, Sharpe 1,32, DD 30 %, 71 obch. vs B&H 50/50 +321 %, 1,71, 34 %; závěrečný ×2 +31,5 % vs B&H −25,1 %, ale DD 60,7 vs 60,0 % a bez top 3 −10,6 tis.). PR #17, `research/ethbtc_switch/RESULTS.md`.
   Poučení: relativní trend pomohl jen v závěrečném období a stojí na 2 úsecích; ve validaci prohrál s držením BTC. Nic neladit podle závěrečného testu.
8. Combined replay (není hypotéza, termín): 1. 12. 2026 nový běh s daty za listopad (viz bod 3 níže).

9. **DALŠÍ NA ŘADĚ →** Pásmový rebalance koše BTC/ETH 50/50 ±5 p. b. vs stejný koš bez rebalance („rebalancing premium“,
   vždy investováno, žádný signál). Liší se od #104 (inverzní volatilita, týdenní rozvrh) i od časování (PR #11–#17).
   PROTOKOL UŽ COMMITNUT (`research/rebalance-band-20261106`, `dc5341a`, `research/rebalance_band/PROTOCOL.md`). Pokračovat: `run.py`
   (loader/metriky z `research/ethbtc_switch/run.py`, PR #17; nová `simulate` se dvěma sleeve a pásmem), testy, workflow, spustit, ověřit, PR.
10. Přepínání XRP ↔ BTC podle trendu XRPBTC (close > SMA50 ⇒ XRP, jinak BTC; vždy investováno), měřítko B&H 50/50 XRP/BTC.
   Liší se od #85 `relative_strength` (XRP vs BTC+ETH 7d, 1h, jen XRP s hotovostí). Pozn.: stejná pravidla jako PR #17, jiné aktivum —
   předem dané, NE laděné podle výsledku PR #17; vyhodnotit stejnými kritérii.
11. Mean-reversion poměru ETHBTC (long-only): výchozí 50/50; z-skóre ETHBTC vůči 20d průměru < −2 ⇒ 100 % ETH do z > 0;
   z > +2 ⇒ 100 % BTC do z < 0. Měřítko B&H 50/50. Liší se od `sol_eth_pairs` (#91, SOL/ETH, jiný pár i mechanika) a od PR #17 (trend).

## Otevřené úkoly (priorita shora)

1. PR #8 čeká na review/schválení vlastníka (merge = deploy). Po nasazení ověřit, že při dalším
   deployi nevznikne duplikát. Zvážit obecnější ochranu (leader lock pro celý obchodní loop, ostatní boty).
2. Kontrola duplicit — HOTOVO 13:10: `tools/autopilot/duplicate_trades_check.sql` (9 tabulek, jen SELECT), krok v RUNBOOK.
   Stav 13:10: bestof 1 skupina (známý id 129), ostatní 0. Chybí FLY/V8 tabulky (jiné schéma, FLY má `fly_trade_exclusions`).
3. Combined replay: export ledgeru HOTOVO (draft PR #9 → research/autopilot, `research/combined_selection_replay/trades/`,
   CONSISTENT, 300 legů; nezávisle přepočteno z trades.csv: 24 bloků, 0 neshod — komentář v PR #9). Dál: 1. 12. 2026 spustit NOVÝ běh s `--end 2026-12-01` (stejný protokol + export),
   výsledky přidat jako nový řádek, předchozí nepřepisovat.
4. Forward PAPER evidence: týdně souhrn ELITE V18/V56, Combined, LH-WHALE, LIQUIDITY, Swing
   (počet, P/L, PF); ≥ 30 nových obchodů na strategii před závěrem. Registr: `automation/STRATEGY_REGISTRY.md`.
5. `test_expired_and_future_signals_never_open` prochází jen formálně — přepsat v PR.
6. `render.yaml` neodpovídá službě (`app_v8_ui` vs `app_v8_fly`) — opravit v PR.

## Rozhodnutí vlastníka 2026-11-05 (11:47 SEČ) — priority dalších běhů

- PR #8: připravit bezpečný plán nasazení (HOTOVO, report výše) — **sloučení ani deploy NESCHVÁLENO**.
- Id 129: návrh tabulky výjimek jen ve výzkumné větvi (HOTOVO: draft PR #10 → research/bestof-dedupe-20261105,
  `b7a77af`, CI 25 passed). **Žádné změny produkční DB ani historických obchodů.**
- Priority: (1) vývoj a testování PAPER strategií, hledání prokazatelně ziskových po VŠECH nákladech
  (nezávislá validace mimo vzorek); (2) Combined replay; (3) kontrola BEST-OF (duplicity, statistiky).
- Šetřit limity: neopakovat úspěšné testy bez důvodu; jeden konkrétní úkol na běh, výsledky hned commitnout.
- Blokace 2026-11-05 11:04 UTC: plánovaný běh selhal — **limit využití účtu (usage limit)**. Při dalším
  selhání to nahlásit vlastníkovi a zkrátit běh na kontrolu + jeden malý úkol.

## Čeká na vlastníka

- Draft PR #10 (návrh výjimky id 129) — review; neprovádět bez souhlasu.
- Draft PR #8 (BEST-OF duplicitní zápis) — vlastník 2026-11-05 10:42 UTC: **ZATÍM NESLUČOVAT**; připraven
  plán nasazení v `reports/bestof-duplicate-129-and-pr8-deploy-plan-20261105.md`, čeká na schválení.
- Id 129: vlastník **NEMAZAT ani NEUPRAVOVAT**. Čtecí analýza hotová (týž report): duplicitní zápis
  uzavření id 128 starou instancí 9r8m5 v 09:14:11 při překryvu deploye; `paper_balance` správně,
  chybně jen statistiky (129/−393,31 místo 128/−383,00). Návrh: tabulka `bestof_trade_exclusions`
  (vzor FLY), vratné DELETE. Neprovedeno — čeká na souhlas.
- Draft PR #9 (Combined ledger export, cíl research/autopilot) — review; produkce se nemění.

## Blokace

- Žádné. Render konektor funguje (čtení). Sandbox nemá PyPI ⇒ testy s FastAPI běží v GitHub Actions
  (lokálně jen se stuby).
