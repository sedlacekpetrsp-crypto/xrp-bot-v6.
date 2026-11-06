# Průřezová disperze fundingu, koš 8 perpů — předem registrovaný protokol (2026-11-06)

Hypotéza `H-20261106-2` z `automation/IDEAS.md` (externí podnět vlastníka). Výhradně PAPER výzkum podle
`automation/RESEARCH_FRAMEWORK.md` v2. Zapsáno a commitnuto **před** prvním kódem, stažením dat i výsledkem.
Po prvním spuštění se pravidla, dělení ani kritéria nemění; povoleny jsou jen dodatky k načítání dat
zapsané před zobrazením jakékoli metriky.

## Odlišnost od otestovaného
- `cross_sectional_rotation` (zamítnuto): řazení podle **ceny** (momentum), ne podle nákladu držení.
- `spot_perp_carry`, `funding_carry` (PR #23), `btc_quarterly_carry`, `sol_basis_convergence`: delta-neutrální carry
  na **jednom** aktivu (spot vs perp), ne relativní řazení napříč aktivy.
- `funding_reversal`, `eth_funding_extreme`, `oi_crowding`: směrový obchod na **jednom** aktivu po extrémní
  úrovni fundingu/pozic, intradenně. Zde: týdenní **long-short koš** podle relativního pořadí.
- Mechanismus: aktiva s nejvyšším fundingem (přeplněné longy) vs nejnižším (přeplněné shorty); výnos = rozdíl
  cenových výnosů + funding inkasovaný shorty z drahých a placený longy levných (u levných často záporný ⇒ inkaso).

## Data (veřejná, bez klíčů; stahuje GitHub Actions — síť session je pro Binance blokovaná)
- Binance Vision USDT-M perpetual: 1h klines `data/futures/um/monthly/klines/<S>/1h/<S>-1h-YYYY-MM.zip` a
  funding `data/futures/um/monthly/fundingRate/<S>/<S>-fundingRate-YYYY-MM.zip`, 2020-08 … 2026-10.
- Koš (pevný, předem): BTCUSDT, ETHUSDT, XRPUSDT, SOLUSDT, BNBUSDT, ADAUSDT, DOGEUSDT, LTCUSDT.
- SHA-256 každého archivu do `data_source.json`. Měsíc archivu, který Binance nemá, protože kontrakt ještě
  neobchodoval, je povolen; aktivum je pak pro daný týden nezpůsobilé (viz níže). Chybějící hodina v klines
  se nedoplňuje; chybí-li cena potřebná pro vstup, výstup nebo funding ⇒ chyba běhu (zastavit, dodatek).
- Funding časy se normalizují na celou hodinu jen při odchylce ≤ 1 s (zavedená konvence repozitáře); větší ⇒ chyba.

## Pravidla (rozhodnutí v pondělí 00:00 UTC)
- Způsobilost aktiva v rozhodnutí D: má funding události i 1h klines souvisle po celé okno W dní před D
  a kontrakt obchoduje v hodině vstupu. Je-li způsobilých < 6 aktiv ⇒ týden se přeskočí (hotovost).
- Signál: `F_W(a) = součet sazeb všech funding událostí aktiva a s časem v (D − W dní, D]` (součet ⇒ srovnatelné
  i při různém intervalu 4h/8h). Používá jen sazby **vypořádané** do D včetně — žádná predikovaná sazba.
- Seřadit vzestupně (shoda ⇒ abecedně podle symbolu). **Long 2 nejnižší, short 2 nejvyšší.**
- Vstup: open 1h svíčky **01:00 UTC** dne D (o hodinu později než rozhodnutí — konzervativní zpoždění exekuce).
- Velikost: každá noha 10 % equity známé při vstupu (4 nohy = 40 % gross), bez páky; zbytek hotovost bez úroku.
- Výstup: open 01:00 UTC dne D + H dní. Pak nové rozhodnutí v den výstupu (D + H je opět pondělí).
  Při H = 14 se signály mezi tím ignorují.
- Funding: u každé události s časem t, kde vstup < t < výstup: cash flow = −strana × sazba × qty × open 1h svíčky
  začínající v t (long platí kladnou sazbu, short ji dostává).
- Likvidace short nohy: marže = notional (1×). Dosáhne-li 1h high ceny 2 × vstup ⇒ ztráta nohy = notional, noha končí
  (`liquidated=1`), ostatní nohy běží dál. Long noha bez páky likvidaci nemá.
- Bez stop-lossu, bez dalších filtrů.

## Náklady
Poplatek 0,095 % + skluz 0,02 % na stranu a nohu (konzervativně nad skutečným taker poplatkem perpů),
náklady ×1 / ×2 / ×3. Funding se nenásobí.

## Mřížka a výběr (4 varianty, N +4)
W ∈ {7, 14} dní × H ∈ {7, 14} dní. Výběr jedné varianty na **ladění ×1 podle čistého zisku**; zvolená se beze změny
použije ve validaci a závěrečném testu. Sousedé = 2 varianty lišící se v jednom rozměru.

## Dělení
- Ladění 2020-10-05 … 2022-12-31 (první rozhodnutí 2020-10-05: SOLUSDT obchoduje od 2020-09, okno 14 dní);
  validace 2023-01-01 … 2024-12-31; závěrečný test 2025-01-01 … 2026-10-31 (podle rámce v2 jen „druhá validace“).
- Koš se otevře jen tehdy, když jeho výstup padne do téhož období; období začíná v hotovosti, 10 000 USDT.
- Walk-forward: kalendářní roky 2021, 2022, 2023, 2024 se zvolenou variantou, náklady ×2.

## Měřítko
B&H koše 8 perpů stejnými vahami (12,5 %), bez rebalance, nákup za open první hodiny období, prodej za close
poslední, stejné náklady; aktivum nedostupné na začátku období se nahradí hotovostí. Informačně: korelace denních
výnosů strategie s BTC (faktorová expozice — long-short není automaticky delta-neutrální).

## Metriky
Denní equity = hotovost + ocenění otevřených noh za close 1h svíčky 23:00 UTC. Sharpe = průměr/sd denních výnosů ×√365.
Max DD z denní equity. „Obchod“ = jedna noha (vstup–výstup), net_pnl včetně fundingu a nákladů. PF z nohou.

## Kritéria (rámec v2, beze změny)
- Stopa A: A1 validace ×1 Sharpe > B&H a max DD < B&H; A2 ≥ 30 obchodů ve validaci; A3 validace ×2 PF > 1,2 a zisk > 0;
  A4 validace ×1 zisk bez 3 nejlepších > 0; A5 závěrečný ×2 zisk > 0, Sharpe > B&H a DD < B&H.
- Stopa B: B1 validace ×2 zisk > 0 a PF > 1,2; B2 max DD ≤ 0,6 × B&H ve validaci i závěrečném testu (×1);
  B3 závěrečný ×2 zisk > 0; B4 validace ×1 bez 3 nejlepších > 0; B5 validace + závěrečný ≥ 20 obchodů; B6 ladění ×1 zisk > 0.
- Při „prošlo“ (A nebo B) navíc: DSR ≥ 0,95 na denních výnosech validace ×1 (`tools/research/deflated_sharpe.py`),
  N = 159 (konzervativně: průběžných 151 + 4 tato + 4 H-20261106-3), V[SR] = 0,5 p.a.; oba sousedé zisk ×2 ve validaci > 0;
  walk-forward zisk ×2 ve ≥ 3 ze 4 let.
- Prošlo vše ⇒ jen **forward PAPER ve výzkumu ≥ 60 dní** (`research/forward/`), nikdy „zisková strategie“
  ani zásah do produkčních botů.

## Kontrola look-ahead (testy kódu před daty)
Rozhodnutí v D se nezmění po připojení dat po D (prefix invariance); sazba s časem > D se do F_W nezapočte;
funding na hranách (t = vstup, t = výstup) se nezapočte; náklady lineárně ×1/×2/×3; likvidace short nohy.

## Hlavní rizika
Squeeze shortované nohy, faktorová (beta) expozice, survivorship bias (koš vybrán v roce 2026 z aktiv, která přežila),
obrat portfolia, malá velikost koše (2 + 2).

## Výstupy
`trades.csv` (každá noha), `results.json`, `RESULTS.md`, `data_source.json`; řádek v `automation/STRATEGY_REGISTRY.md`;
draft PR do `research/autopilot`. Spuštění: commit UTC času do `research/funding_dispersion/RUN_REQUEST`
(nejdřív 2026-11-07 UTC, denní limit 3 nových hypotéz).

## Dodatek 0 (2026-11-06, před kódem i před stažením jakýchkoli dat)
Chybí-li 1h svíčka v čase potřebném pro vstup, výstup, funding, likvidační kontrolu nebo denní ocenění, použije se close
nejbližší dřívější svíčky téhož aktiva nejvýše 6 h zpět (počet náhrad do `results.json`, `price_fallbacks`); starší ⇒ chyba.
Důvod: ojedinělé výpadky hodin na Binance by jinak zastavily celý běh. Pravidla, dělení ani kritéria se nemění.
Shoda v pořadí fundingu se řeší abecedně, výběr varianty při shodě zisku první v pořadí mřížky.
