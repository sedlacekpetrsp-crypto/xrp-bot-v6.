# Průřezové momentum long-short, koš 8 USDT-M perpů, tržně neutrální — předem registrovaný protokol (2026-11-07)

Hypotéza R13 (fronta ve `automation/STATE.md`). Výhradně PAPER výzkum podle `automation/RESEARCH_FRAMEWORK.md` v2.
Zapsáno a commitnuto **před** kódem, stažením dat i jakýmkoli výsledkem. Po prvním spuštění se pravidla, dělení
ani kritéria nemění; povoleny jsou jen dodatky k načítání dat zapsané před zobrazením jakékoli metriky.
Spuštění backtestu až **2026-11-08 UTC po R12** (limit max. 3 nové hypotézy/den; 2026-11-07 vyčerpán R5, R7, R11).

## Mechanismus a odlišnost od otestovaného
- Průřezové momentum (Jegadeesh–Titman 1993; pro krypto Liu–Tsyvinski–Wu 2022 „Common risk factors in cryptocurrency“):
  aktiva s vyšším výnosem za posledních několik týdnů pokračují relativně lépe. Portfolio long vítězové / short poražení,
  dolarově neutrální ⇒ testuje samotnou průřezovou hranu bez expozice vůči trhu.
- `cross_sectional_rotation` (#56) a `relative_strength` (#85) byly long-only spot rotace porovnávané s B&H (směrová
  expozice); R5 (PR #28) řadil podle vzdálenosti od ročního maxima; R11 podle bety; R12 podle MAX. Zde poprvé
  long-short, s fundingem, s volbou vynechání posledního týdne (krátkodobý reversal).
- Očekávání nízké (R5 placebo naznačilo slabé informační pořadí v koši), ale test je levný (sdílí kód R11/R12).

## Data (veřejná, bez klíčů; stahuje GitHub Actions)
Shodná s R11/R12: Binance Vision USDT-M perpetual denní klines + fundingRate 2020-01 … 2026-10, SHA-256 každého archivu
do `data_source.json`; koš BTCUSDT, ETHUSDT, XRPUSDT, SOLUSDT, BNBUSDT, ADAUSDT, DOGEUSDT, LTCUSDT. Loader, ocenění,
funding, likvidace a ošetření mezer beze změny jako R12 (`research/max_effect/PROTOCOL.md`, vč. Dodatku 0 R11).

## Pravidla
- Rozhodnutí v den D (pondělí), vstup za **open dne D**. Signál jen z denních close do **D − 2** včetně.
- Konec okna E = D − 2 − skip. **MOM_i = Π(1 + r_i,t) − 1 přes `lookback` denních výnosů končících E**
  (r = close_t / close_{t−1} − 1). Způsobilé jen aktivum se všemi `lookback` výnosy okna a svíčkou dne D.
- Způsobilých < 6 ⇒ hotovost do dalšího rozhodnutí. Jinak seřadit vzestupně (shoda ⇒ abecedně),
  **long 2 nejvyšší MOM, short 2 nejnižší MOM**.
- Váhy: dolarově neutrální, každá noha 0,15 equity (gross 60 %, long 30 % / short 30 %), bez páky.
- Držení **H = 28 dní** (každé 4. pondělí); výstup za open D + 28, tam hned nové rozhodnutí. Bez stopů a filtrů.
- Funding a likvidace short nohy (denní high ≥ 2 × vstupní fill ⇒ ztráta notional) přesně jako R11/R12.

## Náklady
Poplatek 0,095 % + skluz 0,02 % na stranu a nohu, ×1 / ×2 / ×3. Funding se nenásobí.

## Mřížka a výběr (4 varianty, N +4)
lookback ∈ {28, 56} × skip ∈ {0, 7}. Výběr na **ladění ×1 podle čistého zisku** (shoda ⇒ první v pořadí
LB28_S0, LB28_S7, LB56_S0, LB56_S7); zvolená se beze změny použije ve validaci a závěrečném testu.
Sousedé = 2 varianty lišící se v jednom rozměru.

## Dělení
Ladění 2020-10-05 … 2022-12-31; validace 2023-01-01 … 2024-12-31; závěrečný test 2025-01-01 … 2026-10-31
(použít jednou, nic podle něj neladit). Každý blok začíná v hotovosti 10 000 USDT; první rozhodnutí = první pondělí
≥ začátek bloku; koš se otevře jen, když jeho výstup padne do bloku. Walk-forward: roky 2021–2024, zvolená varianta, ×2.

## Měřítko
B&H koše 8 perpů stejnými vahami bez rebalance a bez fundingu (shodné s R11/R12). Informačně (NE kritérium):
beta ke koši a korelace s BTC; placebo „reversal“ (long poražení, short vítězové) ×1.

## Metriky
Jako R12: denní equity, Sharpe × √365, max DD, „obchod“ = noha (net_pnl vč. fundingu a nákladů), PF z noh.

## Kritéria (rámec v2, beze změny, shodná s R11/R12)
- Stopa A: A1 validace ×1 Sharpe > B&H a max DD < B&H; A2 ≥ 30 obchodů ve validaci; A3 validace ×2 PF > 1,2 a zisk > 0;
  A4 validace ×1 zisk bez 3 nejlepších > 0; A5 závěrečný ×2 zisk > 0, Sharpe > B&H a DD < B&H.
- Stopa B: B1 validace ×2 zisk > 0 a PF > 1,2; B2 max DD ≤ 0,6 × B&H ve validaci i závěrečném testu (×1);
  B3 závěrečný ×2 zisk > 0; B4 validace ×1 bez 3 nejlepších > 0; B5 validace + závěrečný ≥ 20 obchodů; B6 ladění ×1 zisk > 0.
- Robustnost (nutná pro „kandidáta“): DSR ≥ 0,95 na denních výnosech validace ×1, **N = 198** (doložené N = 190 z R10,
  PR #34, + 4 R12 + 4 R13), V[SR] = 0,5 p.a. (rozhoduje); informačně i V[SR] = 0,40 (R10); oba sousedé zisk ×2
  ve validaci > 0; walk-forward zisk ×2 ve ≥ 3 ze 4 let.
- Prošlo vše ⇒ jen **forward PAPER ve výzkumu ≥ 60 dní**, nikdy „zisková strategie“ ani zásah do produkčních botů.
- Pozn.: validace má jen ~26 rozhodnutí × 4 nohy ≈ 104 noh (A2 splnitelné), ale málo nezávislých období ⇒ nízká síla testu.

## Kontrola look-ahead (testy kódu před daty)
Prefix invariance rozhodnutí v D vůči datům od D − 1; MOM odpovídá ručnímu výpočtu včetně skip; nezpůsobilost při mezeře;
dolarová neutralita, 2 + 2 nohy, gross 60 %; držení 28 dní; placebo obrací strany; součet net_pnl v trades.csv = P/L bloku.

## Hlavní rizika
Momentum crash (prudký obrat poražených, short squeeze), malý koš (2 + 2), survivorship bias koše, překryv s R5.

## Výstupy
`trades.csv` (každá noha), `results.json`, `RESULTS.md`, `data_source.json`; řádek v `automation/STRATEGY_REGISTRY.md`;
draft PR do `research/autopilot`. Spuštění: commit UTC času do `research/xs_momentum/RUN_REQUEST`.
