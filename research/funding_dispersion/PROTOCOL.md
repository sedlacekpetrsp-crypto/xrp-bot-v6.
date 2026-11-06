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

## Dodatek 1 (2026-11-06 ~16:20 UTC, po oponentuře ChatGPT, stále před stažením dat a před jakýmkoli výsledkem)
Jen informativní výstupy, kritéria ani pravidla se nemění:
- `edge_funding_events_excluded`: počet funding událostí přesně v čase vstupu/výstupu nohy (01:00 UTC; při 8h/4h intervalu
  by měl být 0; při 1h intervalu by šlo o platbu, kterou protokol nepřiřadí ani staré, ani nové noze).
- `gross_exposure_*` a `bh_vol_matched_x1`: B&H přeškálované na stejnou denní volatilitu jako strategie (návratnost, max DD).
  Důvod: strategie má gross 40 % long-short, B&H 100 % long ⇒ kritérium B2 (DD ≤ 0,6 × B&H) zvýhodňuje nízkou expozici.
  Rozhoduje dál rámec v2; toto číslo slouží jen k poctivé interpretaci.
- Známé zjednodušení (beze změny): funding se počítá z open 1h svíčky last price, ne z mark price; rozhodnutí v 00:00 bere
  sazbu vypořádanou v 00:00 (calc_time o ms později), exekuce je ale až v 01:00 ⇒ žádný fill nepoužívá budoucí informaci.

## Dodatek 2 (2026-11-06 ~16:45 UTC, po oponentuře ChatGPT kolo 2; stále před stažením dat — žádný tržní výsledek dosud neexistuje)
Opravy implementace, aby kód odpovídal textu protokolu (pravidla obchodování, mřížka, dělení ani kritéria se nemění):
- **R1** způsobilost skutečně ověřuje souvislost okna: všechny 1h svíčky v [D − W, vstup] a souvislou funding řadu
  (rozestup sousedních událostí = `funding_interval_hours` dřívější události; chybí-li událost ≤ D ⇒ mezera). Chybějící
  funding se nikdy nepočítá jako nula ⇒ aktivum je ten týden nezpůsobilé (důvod do `ineligible_reasons`).
  Duplicita po normalizaci: stejná hodnota = počítat (`load_audit`), jiná sazba/interval = chyba běhu.
  Mezera funding řady během držení se nepřiřazuje odhadem; noha/koš se označí (`funding_gaps_in_holding`).
- **R2** B&H 8 perpů účtuje skutečný funding (long platí kladnou sazbu, qty × open svíčky v čase události,
  události v (start 00:00, 23:00 posledního dne]); měřítko je tedy skutečně perp benchmark.
- **R3** pořadí v hodině: funding (jen t > vstup) → kontrola likvidace podle high → ocenění; ve výstupní hodině gap
  open ≥ 2 × vstup ⇒ likvidace (ztráta = notional), jinak výstup za open; high po čase výstupu se nepoužívá.
  Omezení ztráty na notional zůstává zjednodušením (bez mark price, udržovací marže a vlivu fundingu na marži).
- **R4** nedefinované DSR (nulový rozptyl, např. 0 obchodů) ⇒ `dsr = null` + důvod, brána neprošla, exporty se zapíší.
- Informativně (bez vlivu na kritéria): náhrady cen podle účelu; metriky z celých košů (`per_basket`); horní mez dopadu
  funding událostí na hranách; scénáře DSR N ∈ {159, 318, 636} × V[SR] ∈ {0,5; 1; 2} p.a. (N = 159 je pracovní odhad,
  ne doložená horní mez); B&H se stejnou volatilitou je jen ex-post diagnostika; „walk-forward“ 2021–24 je roční
  stabilita fixní varianty (pro 2021–22 ne čistý OOS); rozhodnutí v D + 1 s (po zveřejnění sazby vypořádané v D).
- Je-li výsledek „prošlo“, ale existují hrany fundingu, náhrady cen nebo mezery fundingu v držení ⇒ verdikt
  „NEROZHODNUTO“ do ruční revize, ne kandidát.

## Dodatek 3 (2026-11-06 ~17:00 UTC, po oponentuře ChatGPT kolo 3; stále před stažením dat)
- **Výběr jen z informací v D.** Způsobilost = listing, 1h svíčky uzavřené do D ([D − W, D − 1 h]) a souvislý funding
  (D − W, D]. Existence vstupní svíčky (D + 1 h) výběr ani pořadí neovlivňuje. Chybí-li vstupní svíčka vybraného aktiva,
  noha se **neotevře** (slot zůstane v hotovosti, `unfilled_legs`), bez přerankování; při „prošlo“ ⇒ „NEROZHODNUTO“.
  Chybějící data nejsou důkazem, že aktivum nebylo obchodovatelné — jen nehodnotitelnosti.
- **Kontrola dat oddělená od výkonnosti.** Nejdřív běh s `RUN_REQUEST` = `AUDIT …` ⇒ jen `data_audit.json` (všechny přechody
  `funding_interval_hours` s okolními časy a počet nesouladů rozestupu pro sémantiku A „interval od události k další“
  a B „interval úseku končícího událostí“, počet chybějících hodin). Sémantiku rozhodne člověk z konkrétních přechodů
  a zapíše ji sem jako dodatek **před** během výkonnosti; vyjde-li B, kód se upraví a znovu otestuje, teprve pak výkonnost.

## Dodatek 4 (2026-11-06 ~17:00 UTC, pokyn vlastníka; před výpočtem výkonnosti)
Runner odmítne výpočet výkonnosti (kód 3, `PERFORMANCE_REFUSED`) ještě před stažením dat, pokud v této složce chybí
`FUNDING_SEMANTICS.json` s `semantics` ∈ {A, B}, `evidence` a `decided_utc`, nebo pokud rozhodnutá sémantika neodpovídá
implementované (kód implementuje A). Audit dat (`AUDIT`) zámek neblokuje. Rozhodnutí se zapisuje až z `data_audit.json`.

## Dodatek 5 (2026-11-06 ~17:10 UTC, rozhodnutí o sémantice z auditu dat; výkonnost dál nespuštěna)
- Audit run 42256020278 (`data_audit.json`, commit `e037402` — pozor, automatická zpráva commitu chybně říká „backtest
  results“; obsahuje jen audit a manifest, žádné metriky): 7 z 8 aktiv bez přechodu intervalu (vždy 8 h). SOLUSDT 3 přechody
  v 2022-11 (A 2 nesoulady, B 1). Rozhodnuto **B s tolerancí změny uprostřed úseku** (0 nesouladů), detail a evidence
  v `FUNDING_SEMANTICS.json`. Kód (`spacing_ok`, `funding_chain_gaps`) přepnut z A na B; vliv jen SOLUSDT 2022-11-09…19.
- Zámek výkonnosti nově vyžaduje i `performance_hold = false`; zapsané rozhodnutí má `true` (pokyn vlastníka nespouštět
  výkonnost) ⇒ runner výpočet odmítne, dokud to vlastník neuvolní.

## Dodatek 6 (2026-11-06, oponentura kola 4–6 ChatGPT/Claude; výkonnost dál nespuštěna, návrh na kontrolu)
- **Brána výkonnosti (bod 5).** Režim musí být explicitní: `RUN_REQUEST` začíná `AUDIT` nebo `PERF`, cokoli jiného ⇒ kód 4
  bez metrik (dřív „vše nezačínající AUDIT = výkon“). Před načtením dat musí `FUNDING_SEMANTICS.json` kromě dosavadních polí
  obsahovat `audit_id`, `impl_sha256` (= otisk funkcí `spacing_ok`, `funding_chain_gaps`, `funding_window`,
  `funding_completeness`; vypíše `--print-fingerprints`) a `data_manifest_sha256` z auditu. Po načtení a před první simulací
  se otisk skutečně načtených archivů porovná s auditovaným; neshoda ⇒ kód 3, nic se nezapisuje. Audit nevolá simulaci
  a do `audit_manifest.json` uvede své soubory a označí případné staré `results.json`/`trades.csv` jako cizí.
- **Hranice fundingu (bod 2).** Jediná funkce `funding_window`: události s vstup < t < výstup, pro strategii i benchmark.
- **Úplnost fundingu benchmarku (bod 1).** Pro každé skutečně držené aktivum B&H: nesouvislosti, odhad chybějících událostí
  a neznámé pokrytí (bez události před vstupem). Chybějící sazba se nedosazuje nulou. Počty z x1 každého období, bez násobení
  scénáři nákladů. Neznámé pokrytí v držení strategie se počítá jako závada (dřív `None` ⇒ 0).
- **Registr datových závad (bod 3).** Každé počítadlo verdiktu má třídu `blocking`/`informational`; neregistrované ⇒ chyba.
  Blokující > 0 u jinak úspěšného kandidáta ⇒ NEROZHODNUTO. Nově blokují i závady benchmarku (mezery fundingu, náhradní
  ceny, nedostupnost na začátku).
- **Nevyplněné vstupy (bod 4).** Kromě `unfilled_legs` záznam `unfilled_entries` (aktivum, strana, čas, plánovaný notional
  z equity při rozhodnutí, důvod); bez fiktivní pozice, poplatku či cooldownu.
- Zapsané rozhodnutí v `FUNDING_SEMANTICS.json` nová pole nemá a `performance_hold` zůstává `true` ⇒ výkonnost je dál
  odmítnuta. Doplnit pole a uvolnit smí jen vlastník.
