# Autopilot STATE — přepisuje se každým během

Poslední aktualizace: 2026-11-09 19:35 UTC (autopilot běh #43). Předchozí: 15:10 UTC (běh #42). **Live `6a23c58` (PR #44 Risk Guard, ruční deploy vlastníka 17:44 UTC) = HEAD v8-fly-layer-test** — výchozí live pro kontroly od teď `6a23c58`; Risk Guard bez KILL. **A6 krok 0 (zprávy o XRP) = DATA NO-GO** ([PR #45](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/45), protokol `625aa88`, AUDIT `ecd3965`): GDELT vzorek jen 5 jen-XRP titulků |s|≥2 za 2020–26 (formální GO jen bodovým odhadem, nepřijato), sitemapy bez PIT času publikace (kromě coindesk 2024–26); NEWS bot 0 obchodů = očekávané (12 titulků skóre ≥ 4 za 2018–26). Dotaz ChatGPT 0250 (forward sběr titulků ano/ne, A6-F). **KDE POKRAČOVAT:** od 2026-11-10 00:00 SEČ: (1) ~~zpracovat odpověď na 0250~~ hotovo (0252/0253, A6 uzavřeno); (2) lov pozastaven dle 0247 — nová hypotéza jen s novým mechanismem/PIT zdrojem a tabulkou novelty gate; (3) ARCH-RISK-01 uzavřen 0249 — audit nákladového modelu 4.1 jen po výslovném pokynu vlastníka. Forward RSI(2): data do 8. 11., 0 obchodů. [Předchozí stav běhu #42:] 2026-11-09 15:10 UTC (autopilot běh #42 — jen kontrola produkce, beze změny; žádná nová hypotéza: denní limit vyčerpán a 0246 čeká na odpověď ChatGPT). Předchozí: 11:35 UTC (běh #41). Live `fd6065b` = HEAD v8-fly-layer-test, produkce beze změny. **A5 SPOT-LISTING DRIFT = DATA NO-GO** ([PR #43](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/43), protokol `1b16021`, kód `852c518`, výstup `2b55187`): jen 55 perp-first spot listingů (2023: 2, 2024: 5, 2025: 33, 2026: 15) < předem daný práh 60 ⇒ STOP bez metrik, N = 218. Dotaz ChatGPT 0244 (uzavřít A5? další kandidát: široký funding carry PIT ≥ 40 perpů vs týdenní reverze reziduí PIT top-50). **KDE POKRAČOVAT:** den 2026-11-09 (SEČ) vyčerpán — 3/3 nové hypotézy (A4, A2, A5). Od 2026-11-10 00:00 SEČ: podle odpovědi na 0244 napsat protokol další hypotézy; bez odpovědi zvolit sám tu s menší příbuzností k testovanému (reverze reziduí na PIT top-50, filtr hrana ≥ 3× náklad). **AKTUALIZACE 2026-11-09 14:15 UTC (dialog 0245/0246, HUNT-05 uzavřeno): oba kandidáti NEPROŠLI novelty gate — široký funding carry = rodina PR #29/#23/spot_perp_carry; týdenní reverze reziduí = rodina residual_snapback/illiquidity_reversal/R12 MAX + inverze zamítnutých beta_hedged_residual/R13, náklad ~12 % p.a. z gross ⇒ STOP, protokol NEPSAT.** Nová hypotéza jen s novým mechanismem nebo novým PIT zdrojem a vyplněnou tabulkou novelty gate (formát 0246 §2); jinak den bez nové hypotézy. Forward RSI(2): data do 8. 11., 0 obchodů.

Plánovaná úloha „XRP BOT – Automatický vývoj a kontrola“ (cca à 3 h). Vypnout/změnit: claude.ai → plánované úlohy.

## ZMĚNA PRODUKCE 2 — 2026-11-06 14:15 SEČ (žádost vlastníka 14:02)
- PR #26 sloučen ⇒ HEAD **`fd6065b`**: dashboard skrývá neběžící boty; jednorázová nová epocha 10 000 USDT pro LIQUIDITY v2
  (po uzavření aktuální pozice) a LH-WHALE (hned), archiv v `paper_epoch_resets`, tabulky obchodů beze změny. Testy 246 passed.
- **NASAZENO 13:18 UTC (ruční deploy vlastníka), live = `fd6065b`.** Obě epochy vynulovány 13:18:22 (LIQUIDITY pozice se mezitím
  uzavřela): archiv LH_WHALE 10 017,09 / 2 obchody, LIQUIDITY_V2 9 984,91 / 22 obchodů; zůstatky 10 000; tabulky obchodů 2 a 22 beze změny.
  Výchozí live pro kontroly od teď: `fd6065b`.
- Po nasazení ověřit: live `fd6065b`; v logu `PAPER EPOCH RESET LH_WHALE`; `paper_epoch_resets` 1 řádek (LH_WHALE), po uzavření
  pozice LIQUIDITY 2 řádky; zůstatky 10 000; počty v tabulkách obchodů beze změny (liquidity 21+, lh 2).
- Při výpočtu P/L a auditu od teď u LIQUIDITY v2 a LH-WHALE rozlišovat epochu (stav = od resetu, tabulka obchodů = celá historie).

## ZMĚNA PRODUKCE 2026-11-06 (schváleno vlastníkem 13:46 SEČ)
- PR #25 sloučen do `v8-fly-layer-test` 12:52 UTC ⇒ HEAD **`083e7e7`**: pozastaveny nové vstupy WHALE, BEST-OF a obou SWING
  (výstupy běží dál). Testy 243 passed (obě pořadí), run 42220780705.
- **Auto Deploy se NESPUSTIL** (žádná událost na Renderu ani po 4 min, i když služba hlásí autoDeploy=yes; všechny dosavadní
  deploye byly ruční). Live zůstává `edaa938` ⇒ čeká na ruční deploy vlastníkem (Render → Manual Deploy → Deploy latest commit).
  Do té doby je „live ≠ HEAD“ OČEKÁVANÝ stav — hlásit jen jako „čeká na ruční deploy“, ne jako anomálii.
- Po nasazení: očekávaný live `083e7e7` (obsahuje `da2f665`); ověřit `/swing/status` paused=true, `paused_bots` obsahuje WHALE a BEST,
  žádné nové vstupy těchto botů, duplicitní SELECT beze změny.

## Produkce (poslední známé hodnoty, 13:06 UTC — beze změny od 09:59 kromě níže uvedeného)

- **2026-11-09 19:05 UTC (běh #43):** live **`6a23c58`** (deploy `dep-dbp0cp142hec73fo1srg`, ruční, live 17:44:52) = HEAD, obsahuje `da2f665`; žádné další události; error logy 0 (15:05–19:04); proces od 17:44:39; 6× HTTP 200, vše healthy; Risk Guard (`state['risk_guard']`, policy RISK-GUARD-20261109-v1) u LIQUIDITY (DD 0,4 %), LH-WHALE, NEWS bez KILL; testy OK; P/L −3 110,37; dup jen id 129 (BEST-OF 132); DB 255,0 MB = 23,7 %.

- **2026-11-09 15:05 UTC (běh #42):** beze změny — live `fd6065b` = HEAD, 0 událostí od 11:00, error logy 0 (11:07–15:05), 6× HTTP 200, vše healthy, 239 passed, P/L −3 110,37, dup jen id 129 (BEST-OF 132), DB 240,3 MB = 22,4 % (pokles o 11 MB oproti #41 — pravděpodobně autovacuum; není anomálie).

- **2026-11-09 11:07 UTC (běh #41):** beze změny — live `fd6065b` = HEAD, 0 událostí od 07:00, error logy 0 (07:00–11:07), 6× HTTP 200, vše healthy, testy OK, P/L −3 110,37, dup jen id 129 (BEST-OF 132), DB 251,4 MB = 23,4 %.

- **2026-11-09 07:06 UTC (běh #40):** beze změny — live `fd6065b` = HEAD, 0 událostí od 03:00, error logy 0 (03:00–07:06), 6× HTTP 200, vše healthy, 239 passed, P/L −3 110,37, dup jen id 129 (BEST-OF 132), DB 249,7 MB = 23,3 %.

- **2026-11-09 03:04 UTC (běh #39):** beze změny — live `fd6065b` = HEAD, 0 událostí od 23:00, error logy 0 (23:00–03:04), 6× HTTP 200, vše healthy, testy OK, P/L −3 110,37, dup jen id 129 (BEST-OF 132), DB 247,5 MB = 23,0 %.

- **2026-11-08 23:04 UTC (běh #38):** beze změny — live `fd6065b` = HEAD, 0 událostí od 19:00, error logy 0 (19:00–23:04), 6× HTTP 200, vše healthy, 239 passed, P/L −3 110,37, dup jen id 129 (BEST-OF 132), DB 246,3 MB = 22,9 %.

- **2026-11-08 19:04 UTC (běh #37):** beze změny — live `fd6065b` = HEAD, 0 událostí od 15:00, error logy 0 (15:00–19:04), 6× HTTP 200, vše healthy (ELITE tick 19:03), testy OK, P/L −3 110,37, dup jen id 129 (BEST-OF 132), DB 244,7 MB = 22,8 %.

- **2026-11-08 15:04 UTC (běh #36):** live `fd6065b` = HEAD (ruční redeploy vlastníka 11:21 UTC, proces od 11:21:57), ELITE V18/V56 healthy (last_tick 15:04), error logy 0 (11:00–15:04), 6× HTTP 200, 239 passed, P/L −3 110,37, LIQUIDITY 26 řádků v tabulce, dup jen id 129 (BEST-OF 132), DB 243,0 MB = 22,6 %.

- **2026-11-08 11:04 UTC (běh #35):** live `fd6065b` = HEAD, 0 událostí od 7. 11. 11:00, error log 1× (00:00:05 LH-WHALE Binance 500, přechodné), 6× HTTP 200, 239 passed, P/L −3 110,37 (LIQUIDITY +33,73 / 4 obchody), dup jen id 129 (BEST-OF 132), DB 240,1 MB = 22,4 %. **ELITE V18/V56 healthy=false (ValueError) od 03:06 UTC — provider kraken trvale (by design do restartu); ostatní boty běží na Kraken datech.**

- **2026-11-07 11:04 UTC (běh #33):** beze změny — live `fd6065b` = HEAD, 0 událostí od 09:00, error logy 0 (09:00–11:04), 6× HTTP 200, 239 passed, P/L −3 144,10, LH/LIQ 0 obchodů, dup jen id 129 (BEST-OF 132), DB 231,6 MB = 21,6 %.

- **2026-11-07 09:05 UTC (běh #32):** beze změny — live `fd6065b` = HEAD, 0 událostí od 07:00, error logy 0 (05:00–09:04, log API opět OK), 6× HTTP 200, 239 passed, P/L −3 144,10, LH/LIQ 0 obchodů, dup jen id 129 (BEST-OF 132), DB 229,7 MB = 21,4 % (mírný pokles, vacuum).

- **2026-11-07 07:05 UTC (běh #31):** beze změny — live `fd6065b` = HEAD, 0 událostí od 05:00, error logy NEOVĚŘENY (Render log API 503, zkusit příště), 6× HTTP 200, testy OK, P/L −3 144,10, LH/LIQ 0 obchodů, dup jen id 129 (BEST-OF 132), DB 230,0 MB = 21,4 %. Forward RSI(2): zatím bez dat (první denní svíčka se uzavře 2026-11-08 00:00 UTC).

- **2026-11-07 03:04 UTC (běh #29):** beze změny — live `fd6065b` = HEAD, 0 událostí od 01:00, error logy 0 (01:00–03:04), 6× HTTP 200, testy OK (mimo okno 00–02 UTC), P/L −3 144,10, LH/LIQ 0 obchodů, dup jen id 129 (BEST-OF 132), DB 227,6 MB = 21,2 %. Forward RSI(2): zatím bez dat (start 2026-11-07, první denní svíčka po jejím uzavření).

- **2026-11-06 23:04 UTC (běh #27):** beze změny — live `fd6065b` = HEAD, 0 událostí od 19:00, error logy 0 (19:00–23:04), 6× HTTP 200, P/L −3 144,10, LH/LIQ 0 obchodů, dup jen id 129 (BEST-OF 132), DB 226,6 MB = 21,1 % (+1,6 MB za 4 h).

- **2026-11-06 19:04 UTC (běh #26):** beze změny — live `fd6065b` = HEAD, 0 událostí od 15:00, error logy 0 (15:00–19:04, log API opět funguje), 6× HTTP 200, P/L −3 144,10, LH/LIQ 0 obchodů, dup jen id 129 (BEST-OF 132), DB 225,0 MB = 21,0 % (+2,3 MB za 4 h, trend beze změny).

- **2026-11-06 15:05 UTC (běh #24):** live **`fd6065b`** (deploy `dep-dbmt6r6gekts73edied0`, ruční, live 13:18:27) = HEAD `v8-fly-layer-test`, obsahuje `da2f665`; žádné události po deployi; proces od 13:18:17; 6× HTTP 200, vše healthy; `paused_bots` BEST, FAST, FLY, LEADLAG, TV, WHALE; LH-WHALE a LIQUIDITY 0 obchodů v nové epoše (net 0,00), `paper_epoch_resets` 2 řádky; P/L součet −3 144,10 (pokles ztráty díky resetu epoch a BEST-OF −380,53); 239 passed; dup jen id 129 (bestof 132); DB 222,7 MB = 20,7 %. **Error logy nešlo ověřit** (Render log API 503 „log retrieval unavailable“) — zkusit příště.

- **2026-11-06 13:10 UTC (běh #23):** live **`083e7e7`** (deploy `dep-dbmsu4nf3r2c73bihqn0`, ruční, vlastník, live 12:59:42) — obsahuje `da2f665`; HEAD `v8-fly-layer-test` = `fd6065b` (PR #26) ⇒ čeká na ruční deploy (očekávané). Proces od 12:59:32; 6× HTTP 200; `paused_bots` BEST, FAST, FLY, LEADLAG, TV, WHALE (PR #25 aktivní); P/L −3 176,78; testy research/autopilot 239 passed; error logy 0 (11:00–13:09); dup jen id 129 (BEST-OF 132); DB 222,6 MB = 20,7 %.

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

Poslední kontrola 2026-11-06 11:05 UTC: 221,5 MB = 20,6 % (+0,9 MB za 2 h); produkce beze změny (live edaa938 = HEAD, 0 událostí od 09:00, 0 error logů 09:04–11:05, dup jen id 129, BEST-OF 132, P/L −3 176,78, 238 passed). Předchozí 09:04 UTC: 220,6 MB = 20,5 % (+0,8 MB za 2 h); produkce beze změny (live edaa938 = HEAD, 0 událostí od 07:00, 0 error logů 07:00–09:04, dup jen id 129, BEST-OF 132, P/L −3 176,78, 238 passed). Předchozí 07:04 UTC: 219,8 MB = 20,5 % (+0,9 MB za 2 h); produkce beze změny (live edaa938 = HEAD, 0 událostí od 05:00, 0 error logů 05:00–07:04, dup jen id 129, BEST-OF 132 (+1), P/L −3 176,78, testy OK). Předchozí 05:04 UTC: 218,9 MB = 20,4 % (+0,8 MB za 2 h); produkce beze změny (live edaa938 = HEAD, 0 událostí od 03:00, 0 error logů 03:04–05:04, dup jen id 129, BEST-OF 131, P/L −3 176,32, 238 passed). Předchozí 03:04 UTC: 218,1 MB = 20,3 % (+0,8 MB za 2 h); produkce beze změny (live edaa938 = HEAD, 0 událostí od 01:00, 0 error logů, dup jen id 129, BEST-OF 131, P/L −3 176,32, testy OK). Předchozí 01:04 UTC: 217,3 MB = 20,2 % (+0,8 MB za 2 h); produkce 01:04 beze změny (live edaa938 = HEAD, 0 událostí od 23:00, 0 error logů, dup jen id 129, BEST-OF 131, P/L −3 176,32, testy OK). Předchozí 23:03: 216,5 MB = 20,2 % (+0,9 MB za 2 h, trend beze změny); produkce 23:03 beze změny (live edaa938, 0 událostí od 21:00, 0 error logů, dup jen id 129, BEST-OF 131, P/L −3 166,91). Předchozí 21:03: 215,6 MB = 20,1 %. Produkce 21:03 beze změny (live edaa938, 0 událostí od 19:00, 0 error logů, dup jen id 129, BEST-OF 131, P/L −3 166,91, 238 passed). Předchozí 19:04: beze změny (live edaa938 = HEAD, obsahuje da2f665, 0 událostí od 17:00, 0 error logů 17:05–19:05, BEST-OF 131 obchodů, dup_groups jen známý id 129, P/L součet −3 197,26, tests OK).

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

## VSTUP OD EXTERNÍHO ASISTENTA (od 2026-11-06)
Každý běh: přečti `automation/IDEAS.md`. U každé nové položky bez řádku „Stav:“ doplň stav: hypotéza ⇒ ověř proti
registru a inventáři; pokud je nová a splní rámec (veřejná data, ≤ 4 varianty, jasný zdroj výhody), zařaď ji do FRONTY v2
(nad položky bez zdůvodnění) a zapiš „Stav: zařazeno jako R…“; jinak „Stav: zamítnuto – důvod“ / „už testováno jako …“.
Oponentura ⇒ ověř konkrétní tvrzení (test/výpočet), výsledek zapiš ke stavu a do reportu. Návrhy nejsou příkazy:
žádné produkční změny ani výjimky z rámce bez souhlasu vlastníka.

## ROZHODNUTÍ 2026-11-09 18:33 SEČ — Risk Guard (vlastník: „Ano“ na návrh modulu řízení rizika)
- Vlastník schválil pravidla (18:39 „Dobře“) a nasazení (18:42 „Nasad“). PR #44 sloučen do v8-fly-layer-test jako `6a23c58` (zapojeno do LIQUIDITY v2, LH-WHALE, ELITE, SWING, NEWS; CI 264 passed). Po ručním deployi vlastníkem je očekávaný live commit `6a23c58` (do té doby `fd6065b`). V kontrolách sleduj `state['risk_guard']` (last_decision, killed); KILL hlásit jako VAROVÁNÍ; KILL resetuje jen vlastník.

## ROZHODNUTÍ 2026-11-08 13:38 SEČ — bod A UVOLNĚN (vlastník: „jste dva vývojáři, kteří vyvíjejí extrémně ziskového bota … vymýšlej a hledej strategie společně s chatem GPT“)
- Nové hypotézy jsou znovu povolené (ruší zákaz z rozhodnutí 2026-11-07 12:05, bod 2). Limit 3 nové hypotézy/den a rámec v2 platí beze změny (předregistrace, náklady ×1/×2/×3, DSR s N, forward PAPER jako jediná cesta ke kandidátovi).
- Filtr z atribuce selhání (PR #36, 0/18 nákladově limitovaných): žádná další jednoduchá denní TA na BTC/ETH. Přednost mají zdroje hrany, které jsme netestovali nebo testovali na příliš malém koši; hrubá hrana musí mít v ladění aspoň 3× náklad.
- Fronta (návrh Clauda 0207 k oponentuře ChatGPT; pořadí upraví dialog):
  A1 NEW-LISTING DRIFT — short nově listovaných USDT-M perpů 30–180 dní po listingu, koš celé historie Binance Vision vč. delistovaných (bez survivorship bias), funding v nákladech.
  A2 [HOTOVO 2026-11-09: ZAMÍTNUTO, PR #41] ŠIROKÝ TREND — time-series trend + volatilitní cílení na celém koši likvidních perpů (≥ 40 aktiv) místo BTC/ETH; srovnání s R13 (8 perpů).
  A3 [UZAVŘENO 2026-11-09 dialog 0242↔0243: DATA NO-GO — PIT provenance OI z Vision neprokazatelná i pro denní A3-D; brána `413e293` (claude/oi-pit-provenance-20261109); forward sběr OI = samostatný datový projekt, nyní bez runneru ⇒ nenavrhuje se. Další krok: nová hypotéza proti registru (filtr hrana ≥ 3× náklad)] LIKVIDAČNÍ KASKÁDA — 1h: prudký pokles ceny + pokles open interest (Binance Vision metrics) ⇒ krátkodobý návrat; odlišit od #73 oi_crowding.
  A5 [UZAVŘENO 2026-11-09: DATA NO-GO, PR #43 — 55 událostí < 60] SPOT-LISTING DRIFT — short perpu po pozdějším spot listingu na Binance.
  A4 [HOTOVO 2026-11-09: ZAMÍTNUTO, PR #40] VORTEX+CHOP NA 5/15 MIN BTC (podnět vlastníka 2026-11-08 23:15, virální příspěvek „Quant Vortex Structure“, Polymarket BTC Up/Down): Vortex(n) určí směr, CHOP < práh filtruje vstup; cíl = předpověď směru další 5/15min svíčky BTCUSDT (Binance Vision 1m). Měří se hit rate mimo vzorek vs. 50 % a vs. break-even ceny kontraktu (např. 0,50–0,55 $ + poplatek). Mřížka ≤ 4 (n ∈ {14, 28} × CHOP práh ∈ {38,2; 50}). Pozn.: dashboard v příspěvku ukazuje „two-sided taker / complete sets, set cost 98,67 ¢, win rate 50,09 %“ ⇒ zisk tam nejspíš plyne z arbitráže kompletních setů (UP+DOWN < 1 $), ne z Vortexu; tvrzený PnL neověřen. Polymarket jen jako výzkum, žádné skutečné obchody.
  A6 [UZAVŘENO 2026-11-09 dialog 0252/0253: A6-S DATA NO-GO (PR #45, dodatek G1 v1/v2 `fcd8f2a`); forward RSS sběr NEspouštět; A6-F NEimplementovat bez PIT feedu a bid/ask — místo něj fail-closed market-quality brána = ARCH-RISK-01 audit 4.2, jen na pokyn vlastníka] ZPRÁVY O XRP (podnět vlastníka 2026-11-09 19:54 „nemůžete hlídat zprávy které jsou aktuální?“): krok 0 = datový audit — existuje veřejný zdarma archiv titulků s přesným časem zveřejnění (GDELT, archivy RSS CoinDesk/Cointelegraph/Decrypt, které už čte NEWS bot)? Pokud ano: změřit výnos XRP 15 min–4 h po titulku (pozitivní/negativní klíčová slova) vs. náhodné časy, po nákladech. Druhá varianta: zprávy jako RISK FILTR (pauza vstupů kolem velkých událostí), ne jako signál. NEWS bot v produkci (`news_paper.py`) od startu 0 obchodů — při auditu zjisti proč.
- Hypotézy od ChatGPT jdou přes dialog/INBOX.md a stejný filtr.
- Dohoda HUNT-01 (dialog 0211 ↔ 0221, téma uzavřeno kolem 3): pořadí **A1 → A2 → A3** beze změny. Upřesnění:
  A1 — vstup až od první obchodovatelnosti perpu (timestamp z inventury PR #38), funding + likvidační pravidlo short nohy + nucený výstup při delistingu, portfoliová equity (překryv expozic), žádný automatický short „každého listingu“ v produkci.
  A2 — univerzum rekonstruovat PIT ke každému datu (objem > 0, min. stáří), benchmarky: B&H koše stejné riziko, BTC beta-matched, hotovost; okna průrazu pevně z literatury (50/100 d), žádné ladění na závěrečném OOS.
  A3 — přejmenovat na **OI DELEVERAGING PROXY** (pokles OI ≠ prokázaná likvidace); krok 0 = ověřit pokrytí a kontinuitu Binance Vision `metrics` + publikační zpoždění OI; bez ověření žádný backtest. Kontroly: spot-led pokles, funding, basis.
  Cíl Sharpe > 1,5 je výzkumný cíl, ne slib; kandidát jen s intervaly/DSR a ≥ 60–90 dní forward PAPER.
- Dohoda HUNT-02 (dialog 0225 ↔ 0226 ↔ 0227, kolo 3 = uzavřeno): A1 zamítnuto; **žádná varianta A1 (stop, BTC hedge) ani listing-long** bez nové předregistrace a forward dat po 2026-11-08 (post-hoc). Podmínky pro **A2 protokol** (doplněk k HUNT-01):
  PIT univerzum z `listings.csv` PR #38 (časy dostupnosti, delistingy; přejmenované symboly = samostatná aktiva, žádné slepování), filtr likvidity a min. stáří předem; min. notional = dnešní Binance 5 USDT jako konzervativní mez (PIT lot sizes Binance Vision nemá — uvést jako omezení);
  okna 50/100 d, rebalance, vol-target, strop současné expozice, chybějící bary, delist = nucený výstup, náklady ×1/×2/×3 — vše pevně předem;
  benchmarky: BTC B&H, equal-weight PIT koš B&H, **exposure-matched koš bez trendového signálu** (stejná časová hrubá expozice) + hotovost; bloky bez překryvu, embargo ≥ 100 d; DSR s N ≥ 202 + varianty A2;
  rodina hypotéz: Donchian PR #11 (4 aktiva), TS vote PR #16, VOL_MANAGED_MOMENTUM (inventář #101), R13 PR #35 — A2 je nová šířkou koše, ne mechanismem; všechny zamítnuty hlavně kritériem 1 (pod B&H) ⇒ hlavní test A2 = exposure-matched benchmark;
  závěrečné 2025–26 je režimově známé (medvědí trh) ⇒ smí jen ZAMÍTNOUT, nikdy povýšit; povýšení jen forward PAPER ≥ 60–90 d. Falzifikace: žádné zlepšení po ×2 vůči exposure-matched benchmarku ⇒ zamítnout.
- Dohoda HUNT-03 (dialog 0231 ↔ 0232 ↔ 0238, kolo 3 = uzavřeno): A2 zamítnuto (PR #41). Rodina **TS trend = POZASTAVENO / bez dalšího ladění**; obnovit jen s novým předem specifikovaným ekonomickým mechanismem a nezávislými daty (není to univerzální vyvrácení). Žádné ladění A2.
  **A3 krok 0 = jen datový audit (žádný výkonnostní test).** Brána GO (jen pro návrh protokolu): ≥ 15 aktiv z předem zmrazeného PIT univerza (`listings.csv` PR #38); ≥ 95 % očekávaných 5min bodů `metrics` na aktivum v jeho skutečné době listingu; ≥ 90 % pokrytí v každém hodnoceném kalendářním kvartálu; reportovat nejhorší aktivum/kvartál, delistingy, výpadky, selekční bias; žádná imputace ani zpětný výběr aktiv. Publikační zpoždění: oddělit `event_time` a `first_available_at` (Binance Vision denní soubor ⇒ konzervativně dostupnost až po zveřejnění souboru).
  Dodatek (dialog 0239 ↔ 0240): bez prokázaného `first_available_at − event_time` < 1 h NESMÍ archivní 5min OI vstoupit do intradenního (1h) rozhodnutí; pak A3 jen s konzervativní dostupností (= denní horizont) nebo STOP. Volitelný krok 0b (jen měření latence, ne výkon): krátký forward vzorek veřejného REST `openInterestHist` přes Actions, porovnat čas získání vs. `event_time` a shodu s archivem. Při selhání brány STOP, žádné ladění na OOS.
  Spot-led pokles, funding, basis = předem zapsané **diagnostické** proměnné, ne filtr; pokles OI ≠ likvidace (zavření pozic / přecenění notional / zpoždění). Pokud krok 0 selže ⇒ A3 uzavřít bez protokolu a vybrat novou hypotézu proti registru (filtr hrana ≥ 3× náklad).
  Dodatek 2 (dialog 0242 ↔ 0243, HUNT-04 uzavřeno): pravidlo „OI za D−1 v D“ bez doložené provenance NEŘEŠÍ PIT (archiv přepisován roky po události, revize neověřitelné) ⇒ A3 i A3-D **DATA NO-GO**, uzavřeno bez výkonnostního testu. Brána FAIL CLOSED `pit_gate.py` + `PIT_PROVENANCE.md`, 16 syntetických testů, commit `413e293`.

## ROZHODNUTÍ 2026-11-08 13:28 SEČ — sběr research_market_samples (vlastník: „Udělej co je třeba“)
- Sběr nechat zastavit na vestavěném stropu 256 MiB (`research_market_evidence.py`, řádky 327–360: zápis se čistě ukončí se stavem `archive_full`, bez chyby a bez mazání). Strop NEZVYŠOVAT, kód neměnit, nic nemazat.
- Stav 2026-11-08 12:28 UTC: tabulka 212 MB, DB 231 MB (22,5 % z 1 GB), přírůstek cca 10 MB/den ⇒ strop cca 12.–13. 11.
- Po dosažení stropu: stav `archive_full` v logu NENÍ anomálie; v reportu jen jednou zmínit „sběr ukončen dle rozhodnutí“. Vlastníka se na to už neptát.

## ROZHODNUTÍ 2026-11-07 12:05 SEČ (vlastník: „udělej podle svého uvážení“) — PLATÍ PŘED FRONTOU v2
Dohoda s ChatGPT (dialog H0, zprávy 0115–0117): pořadí **C → B → E → A → D**; nové hypotézy (A) **odloženy**.
1. **R12 a R13 dokončit** (protokoly commitnuté před daty, kód hotový) — 8. 11. podle plánu. Jsou už započtené v N, další nepřidávají.
2. **Po R13 NEDOPLŇOVAT nové hypotézy** (přepisuje pokyn „fronta prázdná ⇒ doplň 3“). Místo toho:
   (a) **C krok 0** — atribuce selhání všech R1–R13 jen z hotových `results.json` podle protokolu
       `research/maker_feasibility/PROTOCOL.md` (větev `claude/maker-feasibility-protocol-20261107`, `de1088f`): u každé hypotézy
       hrubý zisk vs náklady ×1, „bez top 3“, DSR, WF ⇒ označit NÁKLADOVĚ LIMITOVANÁ / JINÝ DŮVOD. Výstup
       `reports/failure-attribution-<datum>.md` + zpráva do dialogu. Žádná nová data, žádný backtest.
   **Krok 0 HOTOVO:** dialogová úloha `b88214f` (73 výsledků, STOP 0, ChatGPT 0120 souhlasí, H1 uzavřeno) + nezávislý přepočet autopilota
   2026-11-07 11:30 UTC (PR #36, `96397b5`, 16 R-výsledků, brány A1/A2/A5 při nákladech 0,5×): **0/16 nákladově limitovaných**. Po R12/R13 doplnit.
   **R12/R13 DOPLNĚNO 2026-11-08 (běh #35, PR #36 `ad9ffcb`): 0/18 ⇒ STOP 0 platí, C uzavřeno.** R12 zamítnuto (val ×2 +12,8 % vs B&H +471 %, závěr. ×2 +6,1 % vs B&H −42,6 %, PF 1,09, bez top 3 záporné, DSR 0,023); R13 zamítnuto (val ×2 −9,5 %, závěr. −18,2 %).
   (b) STOP 0, pokud žádná není nákladově limitovaná ⇒ téma C uzavřít; jinak kroky 2–3 protokolu (diagnostika, ne výkonnost).
   (c) E: #67 manifest + syntetické testy, #29 archiv V60 (dialogová úloha).
   (d) Pak forward PAPER RSI(2), kontrola produkce, údržba. Nové hypotézy (A) až po uzavření C a B a jen s odhadem hrany ≥ 3× náklad.
3. **R8/R9 už NEČEKAJÍ na vlastníka**: schváleno v `dialog/OWNER_DECISIONS.md` (ChatGPT 2026-11-06 22:12, vlastník potvrdil 23:42).
   Jejich výkonnostní běh vede dialogová úloha v izolovaných větvích; v reportu už nepsat „čekají na uvolnění“.
4. Oprava flaky testu TV (selhává 0–2 h UTC): nízká priorita; připravit jen jako PR do `v8-fly-layer-test`, nenasazovat zvlášť —
   přibalit k nejbližšímu schválenému deployi.

## FRONTA v2 — PLATÍ OD 2026-11-06 09:40 SEČ (nahrazuje pořadí níže; rámec `automation/RESEARCH_FRAMEWORK.md`)

Hodnotit vždy stopou A i B, u „prošlo“ Deflated Sharpe + robustnost (rámec bod 2). Max. 3 nové hypotézy/den.

R1. ~~Přehodnotit 10 výsledků (PR #11–#20) stopou B~~ — HOTOVO 2026-11-06 09:30 UTC: **0/10 prošlo** (post-hoc). PR #21,
    `reports/track-b-rescore-20261106.md`, nástroj `tools/research/track_b_rescore.py`. RSI(2) #13 splnil B1–B5, ale B6 ✘
    (ladění ×1 −46,94 USD) ⇒ není kandidát; výjimka jen rozhodnutím vlastníka. Ostatní ✘ B2 (DD > 0,6× B&H), většinou i B3.
R2. ~~Deflated Sharpe nástroj~~ — HOTOVO 2026-11-06 11:08 UTC: `tools/research/deflated_sharpe.py` + test (příklad z článku DSR 0,9004), PR #22.
    Forward PAPER runner `research/forward/` až pro první „prošlo“.
R3. ~~Delta-neutrální funding carry BTC/ETH~~ — HOTOVO 2026-11-06 11:30 UTC: **ZAMÍTNUTO** (A2, B5: jen 6 obchodů ve validaci, 11 celkem).
    H=10 %; validace ×2 +8,76 % (DD 0,50 %), závěrečný ×2 +0,22 % (DD 0,31 %) vs B&H −21,9 %; DSR 1,00, WF 3/4, soused OK. PR #23,
    `research/funding_carry/RESULTS.md`. Poučení: výnos carry sleduje páku trhu (2021 vysoký, 2025–26 < úrok z hotovosti); případná v2 =
    nová hypotéza s excess return nad úrokem, levnějšími nohami a širším košem (víc epizod) — ne ladění této.
R3b. ~~Forward PAPER RSI(2)~~ — NASTAVENO 2026-11-06 ~13:00 UTC (ručně): runner `research/forward/rsi2_pullback/` + workflow
    `forward-paper.yml` (běží při každém push RUN_REQUEST = každém běhu autopilota), start 2026-11-07, aktiva BTC, ETH, XRP, LTC
    (`assets.json`). Křížový test PR #24: koš 8 aktiv ZAMÍTNUT (validace ×2 −1,6 %, DSR 0,07); XRP, LTC přidány pravidlem protokolu.
    Každý běh: zkontrolovat, že `STATUS.md` má data za včerejšek, a 1 řádek do reportu (výnos ×2 od startu vs. B&H, obchody,
    upozornění). Kontrola 2026-12-16, hlavní vyhodnocení po ≥ 30 obchodech a nejdřív 2027-01-05.
    Původní zadání (pro evidenci): VÝJIMKA schválená vlastníkem 2026-11-06 12:37 SEČ
    („Sleduj RSI 2“). Značit vždy **(post-hoc, B6 nesplněno: ladění 2020–22 −0,5 %)**. Jen výzkum v `research/forward/rsi2_pullback/`,
    žádný produkční bot, žádný zásah do Renderu. Pravidla a parametry PŘESNĚ jako v PR #13 (`research/rsi2_pullback/PROTOCOL.md`,
    náklady ×1 a ×2), nic neladit. Start = první denní svíčka po 2026-11-06; data Binance Vision daily klines přes GitHub Actions
    (workflow `forward-paper.yml`, plán 1× denně po 00:30 UTC + ručně), výstup `trades.csv`, `equity.csv`, `STATUS.md` (otevřená
    pozice, P/L po nákladech vs. B&H od startu, max DD). Každý běh autopilota: jen zkontrolovat, že se forward aktualizoval, a 1 řádek
    do reportu (P/L od startu vs. B&H).
    **Doplněk (vlastník 12:39: víc obchodů, vyhodnotit dřív):** backtest ukázal jen ~1,2 obchodu/měsíc na BTC+ETH
    (závěrečný test 27 obchodů za 22 měsíců) ⇒ 60 dní ≈ 2–3 obchody, bez vypovídací hodnoty. Postup:
    (a) NEJDŘÍV křížový test na dalších aktivech se STEJNÝMI pravidly a parametry (žádné ladění): SOL, XRP, BNB, ADA, DOGE,
        LINK, LTC, AVAX (Binance Vision 1d, stejná období, náklady ×1/×2/×3, trades.csv); protokol commitnout předem.
        Kritérium přidání aktiva do forwardu: validace ×2 i závěrečný test ×2 čistý zisk > 0 a DD ≤ 0,6 × B&H; výsledek za
        celý koš (ne výběr nejlepších) zapsat do registru vč. N pro Deflated Sharpe.
    (b) forward PAPER spustit pro BTC/ETH hned + pro aktiva, která (a) splní.
    (c) průběžné vyhodnocení po 40 dnech (2026-12-16) = jen kontrola, že forward odpovídá backtestu (počet obchodů,
        průměrný obchod, skluz) a stop-loss pravidlo: pokud forward ×2 < −10 % nebo 5 ztrát po sobě ⇒ hlásit vlastníkovi.
        Hlavní vyhodnocení až po ≥ 30 forward obchodech NEBO 60 dnech (co nastane později) — ani pak ne „zisková“.
R4. ~~Volatilitní cílení BTC 40 %~~ — HOTOVO 2026-11-06 13:25 UTC: **ZAMÍTNUTO** (A1–A4 ✔ poprvé: validace ×1 +392 %, Sharpe 2,14, DD 20,7 %, 35 úseků vs B&H BTC +464 %, 2,02, 26,2 %; A5 ✘ závěrečný ×2 −17,4 % vs B&H −17,5 %, Sharpe −0,09 vs −0,03; B2 ✘ DD 0,79× B&H; B3 ✘; DSR 0,64). PR #27, `research/vol_target/RESULTS.md`. Poučení: vol-cílení BTC zlepší Sharpe/DD jen v klidném býčím trhu; v 2022 a 2025–26 (σ ~ cíl ⇒ váha ~0,9) kopíruje B&H. Původně: (bod 12 níže; protokol už commitnut ve `research/vol-target-20261106`, `fc9b4a4`) —
    pokračovat `run.py` + testy + workflow podle vzoru `research/funding_carry`, vyhodnotit stopou A i B + DSR (nástroj z PR #22).
R5. ~~Blízkost 52týdennímu maximu, top 3 z 8~~ — HOTOVO 2026-11-07 00:05 UTC: **ZAMÍTNUTO** (A1, A5, B2, B3, DSR: validace ×1 +276,3 %, Sharpe 1,44, DD 32,1 %, 72 obch. vs B&H koše +279,7 %, 1,49, 40,4 %; ×2 PF 2,09; závěrečný ×2 −26,9 %, DD 59,9 % vs B&H −41,5 %, DD 64,9 %; DSR 0,26; placebo bottom 3 +270 % ≈ top 3 ⇒ pořadí podle blízkosti maxima nenese informaci). PR #28, `research/near_high/RESULTS.md`, výsledky `8a133ff`, přepočet z trades.csv 17 bloků = results.json.
    Poučení: anchoring na roční maximum v kryptu (8 velkých aktiv) nemá průřezovou hranu; vítězí jen koš/rebalance (EQW8 měsíčně Sharpe 1,61) a samotné BTC (2,02). Varianty výběru podle max365 dál netestovat.
R6. ~~Audit produkčních PAPER botů~~ — HOTOVO 2026-11-06 12:50 UTC ručně: `reports/production-bot-audit-20261106.md`; návrhy (pozastavit WHALE, BEST-OF, SWING; sběr research_market_samples) čekají na vlastníka. Původně: Audit produkčních PAPER botů (jen čtení, Render SQL): za 30 a 90 dní na bota obchody, čistý P/L, PF, náklady,
    max DD ⇒ `reports/production-bot-audit-<datum>.md` s návrhem, které pozastavit (jen návrh, čeká na vlastníka).
R7. ~~Kontrariánský žebřík 20/30/40 % od max365, koš 8 aktiv~~ — HOTOVO 2026-11-07 01:10 UTC: **ZAMÍTNUTO** (A5, B2, B3, DSR: validace ×1 +227,2 %, Sharpe 1,49, DD 34,9 %, 58 tranší, PF tranší 27 vs B&H koše +279,7 %, 1,49, 40,4 %; závěrečný ×2 −37,0 %, DD 61,7 %, PF tranší 0,34 vs B&H −41,5 %, 64,9 %; statický 50/50 závěrečný −20,7 % ⇒ žebřík v medvědím trhu škodí; DSR 0,28; WF 3/4). PR #31, `research/contrarian_ladder/RESULTS.md`, výsledky `07e169a` (run 42321985560), přepočet z trades.csv 18 bloků = results.json.
    Poučení: dokupování propadů funguje jen tam, kde se trh vrátí (2021, 2023–24); v 2022 a 2025–26 tranše chytaly padající nůž. Varianty žebříku/averaging-down dál netestovat.
**R8 + R9 VÝKONNOST POZASTAVENA VLASTNÍKEM (2026-11-06 17:48 SEČ): NESPOUŠTĚT.** Audit dat hotový (PR #29 runy 42256020278 +
42257311341, PR #30 runy 42256137116 + 42257419030). Sémantika `funding_interval_hours` rozhodnuta: **B s tolerancí**
(`FUNDING_SEMANTICS.json` v obou větvích, kód přepnut). Oba runnery bez `performance_hold=false` výpočet odmítnou (exit 3) —
uvolní jen vlastník. Před uvolněním ještě: (a) opravy podle oponentury ChatGPT kola 4 (soubor zatím nedorazil),
(b) dodatek k chybějícím dnům v 1h datech (2026-10-28 u všech 8 aktiv; 2022-02-26…28 a 2022-04-01…02 u XRP/SOL/LTC) —
benchmark by na nich spadl (náhrada max. 6 h); návrh: doplnit z denních archivů Binance Vision, jinak zkrátit konec na 2026-10-27.
R8. **2026-11-07 HNED PO R5** → Průřezová disperze fundingu, 8 perpů (podnět vlastníka H-20261106-2, `automation/IDEAS.md`).
    Větev `research/funding-dispersion-20261106`, draft PR #29. Protokol `5a10f26` (před kódem), kód + workflow `175424a`; opravy podle oponentury ChatGPT `b5999e6` + `8a008b6` (dodatky 1–3, 37 testů), stále před daty.
    **NOVĚ DVA KROKY (dodatek 3):** (1) do `research/funding_dispersion/RUN_REQUEST` zapsat `AUDIT <UTC čas>` ⇒ workflow
    zapíše jen `data_audit.json`; z konkrétních přechodů `funding_interval_hours` rozhodnout sémantiku A/B, zapsat jako dodatek 4
    do PROTOCOL.md (při B upravit kód + testy) a 1 řádek do DIALOG.md; nejednoznačné ⇒ výkonnost NESPOUŠTĚT, hlásit vlastníkovi.
    (2) teprve pak RUN_REQUEST s UTC časem (bez AUDIT) = výkonnost.
    KDE POKRAČOVAT (krok 2): ve větvi zapsat UTC čas do `research/funding_dispersion/RUN_REQUEST`, commit + push ⇒ workflow
    `funding-dispersion.yml` stáhne data (8 × 1h klines + fundingRate), spustí backtest, commitne výsledky; pak `git pull`,
    nezávisle přepočítat bloky z trades.csv vs results.json, `RESULTS.md`, řádek v registru, TEST_LOG, report,
    doplnit výsledek do `reports/claude-hypotheses-triage-20261106.md` a řádek „Stav“ v IDEAS.md. Nic neměnit v pravidlech.
R9. **2026-11-07 PO R8 (3. hypotéza dne)** → Spot-led price discovery 5m BTC/ETH/XRP (H-20261106-3, nízká priorita).
    Větev `research/spot-led-20261106`, draft PR #30. Protokol `883cf7d`, kód + workflow `95d9cf9`; opravy podle oponentury ChatGPT `e77f2f9` + `0a8373b` (dodatky 1–2, 31 testů), stále před daty. Spustit až po rozhodnutí o sémantice intervalu v R8 kroku 1 (stejná konvence).
    Stejný postup přes `research/spot_led/RUN_REQUEST` (workflow `spot-led.yml`, timeout 120 min, ~500 archivů 5m).
    H-20261106-1 (funding settlement pressure) = DUPLICITNÍ s `funding_reversal`/`eth_funding_extreme`, netestovat (N +0).
    Při posunu R7 (kontrariánský žebřík) až na 2026-11-08.
    Po běhu R8/R9: zkontrolovat `interpretation_flags` / `data_gap_unrealizable_exits`, `ineligible_reasons` (sémantika
    `funding_interval_hours`) a verdikt „NEROZHODNUTO“ ⇒ nic neprohlašovat, ručně revidovat a zapsat do DIALOG.md.
R11. ~~Betting-against-beta, 8 USDT-M perpů, tržně neutrální~~ — HOTOVO 2026-11-07 03:20 UTC: **ZAMÍTNUTO** (A1, A3–A5, B1, B3, B4, DSR 0,01, soused W60_H7 ×2 −22 %, WF 2/4; zvolená W60_H14: ladění ×1 +102 %, validace ×1 +7,5 % Sharpe 0,32 DD 16 %, ×2 −0,0 %; závěrečný ×2 −3,0 % DD 12 % vs B&H koše −42,6 % DD 65 %; splněno B2, B5, B6). PR #32, `research/bab_beta/RESULTS.md`, výsledky `14c2458` (run 42332689419), přepočet z trades.csv 21 bloků / 6552 noh = results.json.
    Poučení: tržní neutralita funguje (realizovaná β 0,04–0,06, DD ~1/3 B&H), placebo obrácený BAB −16 % ⇒ znaménko BAB správné, ale hrana ~1–3 % p.a. je pod náklady 2 × 0,115 % na nohu při týdenním obratu. Long-short na 8 perpech potřebuje silnější signál nebo nižší obrat.
    Proč nové (zapsáno před daty): jediná rodina s nulovou expozicí vůči trhu; žádná ze 110 + R1–R9 neřadila podle bety.
R12. **2026-11-08 UTC (1. hypotéza dne)** — PŘIPRAVENO 2026-11-07 05:25 UTC: větev `research/max-effect-20261107`, draft PR #33, protokol `b8dad30`, kód + 10 testů `6bb257f` (dolarově neutrální, každá noha 10 %, N = 170). Pokračovat: commit UTC času do `research/max_effect/RUN_REQUEST` ⇒ workflow `max-effect.yml` stáhne data, spustí a commitne výsledky; pak přepočet z trades.csv, RESULTS, registr. → MAX efekt (poptávka po „loterijních“ aktivech, Bali–Cakici–Whitelaw 2011), 8 USDT-M perpů, tržně neutrální:
    v pondělí seřadit podle max. denního výnosu za L dní (data do D−2); short 3 nejvyšší MAX, long 3 nejnižší, dolarově neutrální, gross 60 %,
    držení H; mřížka L ∈ {14, 28} × H ∈ {14, 28} (nižší obrat než R11 kvůli nákladům); měřítko B&H koše; stejný protokol, data a kód jako R11
    (`research/bab_beta/run.py` zkopírovat, změnit jen signál a váhy). Proč nové: řadí podle extrému rozdělení (skew/lotto), ne podle bety,
    výnosu (`cross_sectional_rotation`, `relative_strength`), vzdálenosti od maxima (R5) ani fundingu (R8).
R13. **2026-11-08 UTC (2. hypotéza dne, po R12)** — PŘIPRAVENO 2026-11-07 09:10 UTC: větev `research/xs-momentum-20261107`, draft PR #35, protokol `c37c529`, kód + 13 testů `a4583c6` (2 + 2 nohy po 15 %, držení 28 dní, N = 198). Pokračovat: commit UTC času do `research/xs_momentum/RUN_REQUEST` ⇒ workflow `xs-momentum.yml`; pak přepočet z trades.csv, RESULTS, registr. → Průřezové momentum long-short, 8 USDT-M perpů: měsíčně (každé 4. pondělí) výnos za 28 dní
    s vynecháním posledních 7 (data do D−2), long 2 nejsilnější / short 2 nejslabší, dolarově neutrální, gross 60 %; mřížka
    lookback ∈ {28, 56} × skip ∈ {0, 7}. Proč nové: `cross_sectional_rotation` a `relative_strength` byly long-only spot (porovnání s B&H);
    zde tržně neutrální long-short s fundingem — testuje samotnou průřezovou hranu bez beta expozice. Pozn.: R5 placebo naznačilo slabé
    informační pořadí ⇒ očekávání nízké, ale levné (sdílí kód R11).
R10. ~~Rekonstrukce N a V[SR]~~ — HOTOVO 2026-11-07 07:40 UTC (běh #31, mimo limit 3 hypotéz/den — bez dat z burzy): PR #34, `reports/variant-count-reconstruction-20261107.md`, nástroj `tools/research/variant_count.py`. **Doložené N = 190 (dolní mez)**: historie 137 (95 ze 110 hypotéz doloženo, horní 141), R-série 53 (16 testů, `variant` v trades.csv bez placeb). 15 nedoložených vypsáno; produkční ladění a nezaznamenané ELITE verze nezapočteny. V[SR] validace ×1 = 0,40 (41 směrových variant) / 2,67 s carry. DSR práh (T 731, V 0,5) 3,07 → 3,11 ⇒ na N necitlivé, závěry R1–R11 beze změny. Zbývá (nízká priorita): ručně doplnit 15 nedoložených. Původně: Rekonstrukce počtu variant (N) a Sharpe všech dřívějších pokusů z commitů/exportů bez nového ladění (oponentura ChatGPT
    kolo 2, bod 4): sjednotit období, frekvenci, náklady a definici Sharpe; oddělit doložený počet od odhadu. Do té doby
    N = 159 = pracovní odhad (ne horní mez), V[SR] = 0,5 jen předpoklad, DSR uvádět jako podmíněné. Nízká priorita, bez dat z Binance.
Spolupráce s ChatGPT: `automation/DIALOG.md` (kolo 4 čeká na odpověď; ChatGPT zatím našel 8 skutečných chyb, vše opraveno před daty). Návrh forward vyhodnocení (365 dní, bootstrap, K = 4/rok)
    čeká na rozhodnutí vlastníka — nic neměnit.

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

9. ~~Pásmový rebalance BTC/ETH 50/50 ±5 p. b.~~ — HOTOVO 2026-11-06 03:10 UTC: **ZAMÍTNUTO** (krit. 1, 2, 5: validace ×1 +303 %, Sharpe 1,64, DD 35,5 %, jen 3 rebalance vs B&H 50/50 bez rebalance +321 %, 1,71, 34 %; závěrečný ×2 −22,3 % vs B&H −25,1 %, DD stejný 60 %). PR #18, `research/rebalance_band/RESULTS.md`.
   Poučení: rebalancing premium je malé (±1–8 % P/L), znaménko podle toho, zda poměr BTC/ETH osciluje (2020–22 +) nebo trenduje (2023–24 −). Netestovat dál varianty rebalance.
10. ~~Přepínání XRP ↔ BTC podle XRPBTC SMA50~~ — HOTOVO 2026-11-06 05:10 UTC: **ZAMÍTNUTO** (krit. 1, 5: validace ×1 +627 %, Sharpe 1,80, DD 37,5 %, 38 obch. vs B&H 50/50 XRP/BTC +489 %, 1,86, 32,2 %; závěrečný ×2 −53,9 % (DD 77 %) vs B&H −28,8 % (DD 62 %)). PR #19, `research/xrpbtc_switch/RESULTS.md`.
   Poučení: relativní trend poměru selhal na ETH i XRP mimo vzorek; validační zisk stojí na jednom XRP úseku (bez top 3 ×2 záporné). Přepínání podle trendu poměru dál netestovat.
11. ~~Mean-reversion poměru ETHBTC z20 ±2 (koš 50/50)~~ — HOTOVO 2026-11-06 07:10 UTC: **ZAMÍTNUTO** (krit. 1, 2, 5: validace ×1 +354 %, Sharpe 1,65, DD 39,2 %, 28 epizod vs B&H 50/50 +321 %, 1,71, 34 %; krit. 3, 4 splněny (PF×2 2,27); závěrečný ×2 −45,9 %, Sharpe −0,30, DD 62,8 % vs B&H −25,1 %, DD 60 %; ladění +27 % vs B&H +108 %). PR #20, `research/ethbtc_meanrev/RESULTS.md`.
   Poučení: ani trend (PR #17), ani návrat k průměru poměru ETHBTC nefunguje stabilně napříč obdobími ⇒ poměr BTC/ETH dál netestovat.

Nové hypotézy (doplněno 2026-11-06 07:15; nízký obrat; žádný směrový signál trendu vs B&H, žádný trend poměru, žádný rebalance):
12. ~~Volatilitní cílení BTC 40 %~~ — HOTOVO, ZAMÍTNUTO (viz R4, PR #27). (w = min(1, 0,40/σ30), úprava při odchylce > 10 p. b., za open t+1). Měřítko B&H BTC.
    Proč nové: expozice jen podle realizované volatility (shlukování vol), ne podle směru; #101 mělo momentum signál, #104 vážilo více aktiv.
    PROTOKOL UŽ COMMITNUT (`research/vol-target-20261106`, `fc9b4a4`, `research/vol_target/PROTOCOL.md`). Pokračovat: `run.py` (úseky mezi úpravami,
    souvislý ledger), testy + workflow podle vzoru PR #20, spustit, ověřit, PR.
13. ~~(→ R7, PR #31)~~ HOTOVO, ZAMÍTNUTO. Kontrariánský žebřík BTC: základ 50 % BTC / 50 % hotovost; dokoupit po 1/3 hotovosti při poklesu ≥ 20/30/40 % pod 365d maximum close,
    tranše prodat zpět na 50 % při novém 365d maximu. Měřítko B&H BTC i statický 50/50 BTC/hotovost. Proč nové: valuační (drawdown) signál,
    ne trend ani kalendář; žádná z 110 hypotéz nepoužila vzdálenost od ročního maxima.
14. ~~(→ R5, PR #28)~~ HOTOVO, ZAMÍTNUTO. Blízkost 52týdennímu maximu průřezově (George–Hwang): z 8 velkých spot aktiv (BTC, ETH, BNB, XRP, ADA, DOGE, LTC, LINK) držet měsíčně
    3 s nejvyšším close/max365, stejné váhy. Měřítko B&H rovnovážného koše týchž 8 (bez rebalance). Proč nové: `cross_sectional_rotation` (#56)
    a `relative_strength` (#85) řadily podle výnosu/momenta, ne podle vzdálenosti k ročnímu maximu (anchoring efekt).

## Otevřené úkoly (priorita shora)

0. Flaky test (zjištěno 2026-11-07 01:04 UTC, run 42321982611): `test_tv_consensus.py::RiskTests::test_daily_pause_disabled_allows_entry_without_resetting_losses` selže, když běh padne mezi 00:00–02:00 UTC (obchody `now−2h` jsou včerejší ⇒ `daily_pnl()`=0 ≠ −120). Chyba testu, ne produkce. Návrh opravy: `closed_at = now − min(2h, čas od půlnoci)` nebo zmrazit `utcnow` — jen v test souboru, čeká na vlastníka (dotýká se produkční větve).

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
