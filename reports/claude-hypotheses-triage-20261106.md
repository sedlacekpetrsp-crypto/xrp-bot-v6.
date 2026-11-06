# Triage podnětů vlastníka 2026-11-06 (CLAUDE_HYPOTEZY_20261106.md)

Ruční běh Clauda 2026-11-06 ~15:55 UTC, větev `research/autopilot`. Výhradně PAPER; žádný zásah do Renderu, DB,
`main` ani `v8-fly-layer-test`; nic se nezařazuje do produkčních botů.

**Proč zatím nejsou čísla:** rámec v2 bod 4 povoluje max. 3 nové hypotézy denně a limit na 2026-11-06 vyčerpaly
R3 (funding carry, PR #23), RSI(2) křížový test (PR #24) a R4 (vol-target, PR #27). Proto jsou dnes jen předem
zmrazené protokoly, kód a testy; backtesty se spustí 2026-11-07 UTC spolu s R5 (= 3 hypotézy toho dne).
Data z Binance Vision ze session nejdou (proxy odmítá data.binance.vision) ⇒ stahování a výpočet běží v GitHub Actions.

| Hypotéza | Stav | Podobné protokoly | Protokol (commit) | Kód / PR | N |
|---|---|---|---|---|---|
| H-20261106-1 Funding settlement pressure | **DUPLICITNÍ** – netestováno | `funding_reversal` (39b2eb1), `eth_funding_extreme` (6b7e254), `premium_recovery` (879655d), `funding_carry` PR #23 | — | — | +0 |
| H-20261106-2 Cross-sectional funding dispersion | **ZAŘAZENO (R8)** | `cross_sectional_rotation`, `spot_perp_carry`, `funding_carry`, `oi_crowding`, `funding_reversal` – bez překryvu mechanismu | `5a10f26` + dodatek 0 v `175424a` | `175424a`, PR #29 | +4 |
| H-20261106-3 Spot-led price discovery | **ZAŘAZENO (R9, nízká priorita)** | `flow_pressure`, `btc_lead_lag` (částečně), `large_trade_followthrough`, `cross_exchange_residual` | `883cf7d` + dodatek 0 v `95d9cf9` | `95d9cf9`, PR #30 | +4 |

Průběžné N pro Deflated Sharpe: 151 (po R5) + 4 + 4 = **159** — **pracovní odhad**, ne doložená horní mez (základ 140 je odhad pro 110 historických hypotéz; rekonstrukce = úkol R10). Oba runnery vypisují i scénáře N 159/318/636 × V[SR] 0,5/1/2.

## H-20261106-1: Funding settlement pressure — DUPLICITNÍ

- Jádro pravidla je doslova pravidlo `funding_reversal` (XRP, protokol `research/funding_reversal_protocol.md` ve větvi
  `autocorr-regime-research-20261024`): po uzavřeném funding záznamu sazba ≤ 10. percentil předchozích 90 záznamů
  (aktuální vyloučen) ⇒ obchod proti znaménku za open další svíčky. Výsledek: 15 OOS kvartálů 2023 Q1–2026 Q3,
  321 obchodů, −1 403,59 USD, PF 0,76 (×2: −2 754,20, PF 0,59), kladné jen 4 kvartály, kontrola 2022 také ztrátová.
  Mechaniku nezávisle ověřil audit (PASS).
- `eth_funding_extreme` (větev `eth-funding-extreme-research-20261024`): po settlementu ETH s |sazba| ≥ 0,020 % proti
  znaménku za další hodinový open, 24 h ⇒ NEPROŠEL.
- Basis filtr (perp-spot znaménko) je pozorovatelná veličina zamítnutého `premium_recovery` (PF 1,09, ×2 0,89).
- Co je nové: obě strany, držení 60/120 min, BTC+ETH, exekuce na perpu, 5m. To jsou parametrické varianty téhož
  mechanismu („extrémní funding po settlementu ⇒ krátkodobý návrat“) na obdobích, která už tento mechanismus viděl;
  autoři `funding_reversal` i `oi_crowding` výslovně doporučili další varianty derivátového crowdingu na těchto
  obdobích netestovat. Test by jen zvyšoval N.
- Dostupnost dat (pro případné znovuotevření): testovatelné bez look-ahead — `fundingRate` archivy mají `calc_time`
  vypořádání (sazba je známá v čase settlementu), spot i perp 5m klines jsou na Binance Vision.
- Pozn. k pravidlu „funding jen při držení přes settlement“: při vstupu po settlementu a výstupu po 60–120 min pozice
  nikdy nedrží přes další settlement (interval 4–8 h) ⇒ funding cash flow by byl vždy nulový; výnos by stál jen na ceně.
- Verdikt: **netestovat**. Znovuotevřít jen rozhodnutím vlastníka a jen jako čistě forward PAPER (bez historického výběru).

## H-20261106-2: Cross-sectional funding dispersion — ZAŘAZENO (R8)

- Odlišnost: jediná dosavadní průřezová strategie (`cross_sectional_rotation`) řadila podle ceny; všechny funding/basis
  testy byly na jednom aktivu. Relativní pořadí nákladu držení v long-short koši testováno nebylo.
- Data: Binance Vision USDT-M 1h klines + `fundingRate`, 8 aktiv, 2020-08…2026-10. Funding se bere jen vypořádaný do
  rozhodnutí (pondělí 00:00 UTC), vstup až 01:00 ⇒ bez look-ahead. SOLUSDT perp obchoduje od 2020-09 ⇒ ladění od
  2020-10-05. Chybějící měsíce povoleny jen před listingem; chybějící hodina ⇒ close nejbližší dřívější ≤ 6 h (dodatek 0,
  počet do výsledků); jinak běh skončí chybou.
- Zmrazená pravidla: long 2 nejnižší / short 2 nejvyšší podle součtu sazeb za W dní, 10 % equity na nohu (40 % gross),
  bez páky, výstup po H dnech; skutečný funding mezi vstupem a výstupem; likvidace short nohy při 2× ceně.
  Mřížka W ∈ {7, 14} × H ∈ {7, 14}, výběr na ladění ×1. Dělení ladění 2020-10…2022, validace 2023–24,
  závěrečný 2025-01…2026-10 (jen „druhá validace“). Měřítko B&H 8 perpů stejnými vahami; info korelace s BTC.
- Testy mechaniky (9): výběr noh, kauzalita signálu (sazba po D se nezapočte), prefix invariance, znaménko a hrany
  fundingu, linearita nákladů, likvidace, P/L long/short, přeskočení týdne při < 6 způsobilých aktivech.
- Rizika předem: squeeze short nohy, beta expozice, survivorship bias (koš vybraný v 2026), malý koš 2 + 2.

## H-20261106-3: Spot-led price discovery — ZAŘAZENO (R9, nízká priorita)

- Překryv: `flow_pressure` používal taker-buy podíl (XRP 15m, spot long) a byl zamítnut (PF 0,82, ×2 0,38);
  `btc_lead_lag` testoval lead-lag mezi aktivy (1h, 50 OOS obchodů, PF 0,73). Nové je jádro „spot se pohnul, perp
  téhož aktiva ještě ne“ s obchodem na perpu v obou směrech. Rámec v2 bod 5 dává přednost carry/průřezu ⇒ až po R8.
- Data: Binance Vision spot 5m (sloupec 9 taker buy base) + perp 5m + funding, BTC/ETH/XRP 2020-01…2026-10. Párování
  jen přes shodný open time (µs spot časy převedeny na ms), nic se nedoplňuje, audit mezer do výsledků.
- Zmrazená pravidla viz `research/spot_led/PROTOCOL.md`; vstup až na perp open následující svíčky, výstup po 15/30 min,
  1 pozice na aktivum, 10 % equity. Round-trip náklady 0,23 % (×1) — protokol vypisuje průměrný hrubý výnos obchodu v bp,
  aby bylo vidět, zda hrana vůbec přesahuje náklady.
- Testy mechaniky (11): příznaky jen z T a T−5m, vstup za T+5m, prahy, blokace když perp už reagoval, bez překryvu,
  chybějící vstup/výstup, hrany fundingu, prefix invariance, linearita nákladů a sesouhlasení equity, výstup v období,
  audit mezer. Syntetický běh v plné velikosti: 12 s, 1,4 GB RAM.
- Riziko předem (hlavní): rozdíl close spot vs perp v 5m okně je z velké části artefakt času posledního obchodu a do
  open další svíčky zmizí; nízká apriorní pravděpodobnost.

## Výsledky po nákladech ×1/×2/×3, obchody, Sharpe, max DD, PF, DSR, robustnost

H1: netestováno (duplicita). H2 a H3: **zatím žádné** — doplní se do tohoto souboru, `automation/STRATEGY_REGISTRY.md`
a `automation/REPORTS.md` po backtestu 2026-11-07. Kandidát by byl jen „k forward PAPER ≥ 60 dní“, nikdy „ziskový“.

## Jak spustit (2026-11-07 UTC a později)
V příslušné větvi zapsat UTC čas do `research/funding_dispersion/RUN_REQUEST` (resp. `research/spot_led/RUN_REQUEST`),
commit + push ⇒ workflow stáhne data, spustí testy a backtest a commitne `results.json`, `trades.csv`, `data_source.json`.
Pak nezávisle přepočítat bloky z `trades.csv` proti `results.json`, napsat `RESULTS.md`, řádek do registru a reportu.
Pokud běh skončí chybou dat, smí se protokol doplnit jen dodatkem k načítání dat **před** zobrazením metrik.
