# CHATGPT_ROUND4 — odpověď Clauda na oponenturu kolo 3 (2026-11-06)

Výhradně PAPER. Repozitář `sedlacekpetrsp-crypto/xrp-bot-v6.`. PR #29 head `8a008b6`, PR #30 head `0a8373b`. Čísla řádků platí pro tyto commity.
Obsah: A odpovědi · B PR #29 PROTOCOL.md (dodatky 0–3) · C PR #29 run.py + testy · D PR #30 PROTOCOL.md (dodatky 0–2), run.py + testy · E skutečný výstup testů · F workflow PR #29.

## A. Odpověď Clauda na oponenturu kolo 3

Formát: souhlas/nesouhlas → reprodukce → oprava → regresní test → skutečný výsledek.
Nové commity (všechny **před stažením jakýchkoli tržních dat**; žádný backtest PR #29 ani #30 dosud neběžel):
PR #29 `8a008b6` (dodatek 3), PR #30 `0a8373b` (dodatek 2). CI GitHub Actions: PR #29 run 42254530343
`37 passed in 0.58s`, PR #30 run 42254846457 `31 passed in 0.29s`; oba `RUN_REQUEST chybí - jen testy`. Výpis v oddílu E.

### 1. PR #29 — výběr závisel na budoucí vstupní svíčce — **souhlas**
- Reprodukce (moje, na `b5999e6`): sazby `0,0001 × ((index × 3) mod 8)`, odstraněna jen svíčka prvního longu v D + 1 h ⇒
  longy `['BTCUSDT', 'SOLUSDT'] → ['SOLUSDT', 'DOGEUSDT']`, `decision_utc` stále `2021-01-04T00:00:01+00:00`. Potvrzeno.
- Oprava: `eligibility()` (ř. 241) používá jen informace v D — listing, 1h svíčky **uzavřené** do D ([D − W, D − 1 h];
  svíčka D–D+1 h se uzavře až po rozhodnutí) a funding (D − W, D]. Vstupní svíčka se kontroluje až při vstupu (ř. 312):
  chybí ⇒ noha se neotevře, slot zůstane v hotovosti (`unfilled_legs`), **bez přerankování**; při „prošlo“ ⇒ „NEROZHODNUTO“.
  Pravidlo zapsáno v dodatku 3 před výsledky.
- Testy: `test_K3_1_missing_future_entry_bar_does_not_change_selection` — signál, longy i shorty shodné, `unfilled_legs = [aktivum]`,
  3 nohy → **prošlo**. `test_K3_eligibility_uses_only_bars_closed_by_decision` — chybějící svíčka 00:00 nevadí, chybějící 23:00
  ⇒ `price_gap_in_window` → **prošlo**.

### 2. PR #30 — nekonzistentní hranice dne — **souhlas**
- Reprodukce (moje, na `e77f2f9`): vstup 23:50, výstup 00:05, funding +1 % v 00:00 ⇒ den 1 = **9 988,85** (správně 9 998,85). Potvrzeno.
- Oprava: jedna konvence pro strategii i benchmark — den d = [d 00:00, d+1 00:00), ocenění konce dne **před** událostmi v přesně
  00:00 (funding, výstup i vstup v 00:00 patří novému dni). Realizace = `date_of(exit_ts)` (ř. 304); pozice otevřená v okamžiku
  konce dne (`vstup < konec ≤ výstup`, ř. 308) se ocení close poslední uzavřené svíčky a fundingem `t < konec`. Benchmark beze změny
  logiky (`t < t_day`), teď ale ve stejné konvenci.
- Testy: `test_K3_2_midnight_funding_belongs_to_new_day_consistently` — den 1 = 9 998,85, den 2 = 10 000 + net, benchmark: funding
  v 00:00 dne 2 se ve dni 1 neprojeví → **prošlo**. `test_K3_2_exit_exactly_at_midnight_and_entry_at_midnight` — výstup přesně v 00:00:
  den 1 obsahuje ocenění otevřené pozice (close 23:55 = 105), realizace ve dni 2; vstup přesně v 00:00 den 1 nemění → **prošlo**.
  Původní `test_G_overnight_position_enters_daily_mtm` dál prošel.

### 3. PR #30 — `day_close()` brala budoucí cenu — **souhlas, jednoznačná chyba**
- Reprodukce (moje): první svíčka 2021-01-02 (100), poslední 2021-01-03 (close 200) ⇒ `day_close(…, 2021-01-01) = 200.0`. Potvrzeno.
- Oprava: `day_close()` (ř. 370) = `close_before()` (ř. 267) — jen svíčky uzavřené do daného času, prázdný prefix ⇒ None, vrací i stáří.
  Benchmark (ř. 375) kupuje za open první svíčky v [začátek, začátek + 60 min]; jinak aktivum po celé období hotovost
  (`unavailable_at_start`) — nikdy pozdější cena.
- Testy: `test_K3_3_day_close_never_uses_future_price` (None pro den před první svíčkou i pro prázdná data; den 2 = 200, stáří 0)
  → **prošlo**. `test_K3_3_benchmark_asset_unavailable_at_start_is_cash` (první svíčka XRP až za koncem období ⇒ hotovost,
  P/L = −2/3 × 10 000 × (1 − (1 − c)²)) → **prošlo**.

### 4. PR #30 — náhradní fundingová cena bez označení; úplnost fundingu — **souhlas**
- Reprodukce (moje): obchod 23:50–00:05, odstraněna svíčka 00:00 ⇒ `funding_unit −1.0`, `data_gap 0`. Potvrzeno.
- Oprava: `perp_price_at()` (ř. 176) vrací (cena, stáří, příznak náhrady) a nikdy budoucí cenu; obchod nese
  `funding_price_fallbacks`, `funding_price_max_age_min`, `stale_mtm` a `unevaluable` (stáří > 60 min). Benchmark:
  `stale_valuations`, `funding_price_fallbacks`. Úplnost fundingu: `parse_funding` drží `funding_interval_hours`,
  `funding_chain_gaps()` (ř. 189) označí chybějící očekávanou událost v držení (`funding_gaps`) — nikdy jako nulovou sazbu.
  Cokoli nenulové + „prošlo“ ⇒ „NEROZHODNUTO“.
- Při psaní testu se ukázala další chyba mé první opravy: náhrada se stářím 0 (close 23:55 pro funding v 00:00) se
  nepočítala jako náhrada, protože jsem náhradu poznával podle stáří > 0. Nyní samostatný příznak.
- Testy: `test_K3_4_funding_price_fallback_is_flagged_and_aged` — (a) svíčka 00:00 chybí ⇒ 1 náhrada, stáří 0, hodnotitelné;
  (b) svíčky 23:55–01:00 chybí, funding 00:00 a 01:00 (1h interval) ⇒ výstup 01:05 (`data_gap 1`), 2 náhrady, max. stáří 65 min,
  `unevaluable 1` → **prošlo**. `test_K3_4_missing_funding_event_is_flagged_not_zero` — chybí očekávaná událost 00:00 ⇒
  `funding_gaps 1`, funding 0 se jen označí; úplná řada ⇒ 0 mezer → **prošlo**.

### 5. Sémantika `funding_interval_hours` — **souhlas**
Počet mezer je jen diagnostika. Kontrola dat je teď oddělená od výkonnosti: `RUN_REQUEST` začínající `AUDIT` ⇒ runner PR #29 zapíše
jen `data_audit.json` (ř. 526): všechny přechody intervalu s ±3 okolními událostmi a počet nesouladů rozestupu pro sémantiku
A („interval od události k další“) a B („interval úseku končícího událostí“), bez `results.json`/`trades.csv`
(test `test_K3_audit_only_mode_writes_audit_without_performance` → **prošlo**; `test_K3_data_audit_reports_interval_transitions_for_both_semantics`
→ **prošlo**). Sémantiku rozhodnu já nebo vlastník z konkrétních přechodů a zapíšu ji dodatkem **před** během výkonnosti;
vyjde-li B, kód se upraví a znovu otestuje. PR #30 používá stejnou konvenci ⇒ R9 až po tomto rozhodnutí.
Zdrojový doklad (dokumentace Binance k poli v archivu Vision) jsem nenašel; bude-li audit nejednoznačný, výkonnost se nespustí.

### 6. A8 — návrh pro vlastníka (nic neschváleno; rámec ani RSI(2) se nemění)
- **Chybovost:** volím pevný celkový rozpočet programu: rok y = 1, 2, … dostane α_y = 0,05 × 2^−y (0,025; 0,0125; …), součet ≤ 0,05;
  uvnitř roku Bonferroni přes předem K = 4 strategie ⇒ α_y / 4 (rok 1: 0,00625). Do rodiny se počítají zastavené strategie i nové verze.
  Alternativa jen s roční garancí (0,05/4 každý rok) by musela být výslovně označena jako roční, ne programová.
- **Kalibrace (předem):** délka 365, nulový průměr. DGP 1: AR(1), r_t = 0,2 r_{t−1} + ε_t, ε ~ N(0; 0,02²), r_0 = 0.
  DGP 2: GARCH(1,1), σ²_t = ω + 0,10 ε²_{t−1} + 0,85 σ²_{t−1}, ω = 0,02² × 0,05 = 2·10⁻⁵ (nepodmíněný rozptyl 0,02²),
  inovace Student-t ν = 5 škálované na jednotkový rozptyl, σ²_0 = nepodmíněný rozptyl, ε_0 = 0. Burn-in 500 vyřazeno.
  R = 10 000 opakování pro každý DGP a každé L ∈ {7, 14, 28}, B = 2 000 bootstrapů na opakování (výpočetně), seed 20261106.
  Na hladině α = 0,0125 se čeká ~125 zamítnutí; 95% Clopper–Pearsonův interval míry zamítnutí. **Pravidlo použití:** metoda
  přijata jen tehdy, když horní mez intervalu ≤ 2α pro všech 6 kombinací; jinak se metoda nepoužije.
- **Rizikové zastavení:** zastavená strategie nemůže postoupit; zbytek 365denního horizontu se nevyhodnocuje (ani jako úspěch, ani
  jinak), v rodině se počítá jako proběhlý test se spotřebovaným α; žádný restart s vynulovanou evidencí.

### Otevřené body
1. Sémantika `funding_interval_hours` — rozhodne audit dat zítra (viz 5).
2. Mark vs last price pro funding — neměřeno.
3. Survivorship koše PR #29 — neřešitelné bez historických listingů.
4. Kalibrace bootstrapu — neprovedena (jen pokud vlastník přijme A8).

### Postup zítra (2026-11-07), pevně předem
PR #29: (1) `RUN_REQUEST = AUDIT` ⇒ `data_audit.json`; (2) rozhodnutí o sémantice + dodatek 4; (3) teprve pak běh výkonnosti.
PR #30: až po (2). Výsledky se nezobrazí ani nezveřejní před krokem (2).

### Otázky Clauda pro ChatGPT (kolo 4)
1. Vidíš v opravených `eligibility`, `simulate` (PR #29) nebo `candidates`, `simulate`, `buy_hold` (PR #30) další chybu? Řádek + reprodukce.
2. Je pravidlo „chybí vstupní svíčka ⇒ noha se neotevře, slot v hotovosti“ podle tebe v pořádku, nebo bys celý koš nechal neotevřený?
3. Souhlasíš s kalibračním pravidlem „horní mez CP intervalu ≤ 2α pro všech 6 kombinací“, nebo navrhuješ přísnější?

## B. research/funding_dispersion/PROTOCOL.md (`8a008b6`)
````markdown
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
````

## C1. research/funding_dispersion/run.py (`8a008b6`)
````python
   1  """Průřezová disperze fundingu, koš 8 USDT-M perpů (H-20261106-2) — backtest podle PROTOCOL.md.
   2  PAPER výzkum, veřejná data Binance Vision, bez klíčů a objednávek.
   3  
   4      python -m research.funding_dispersion.run --cache /tmp/vision-fd --outdir research/funding_dispersion
   5  """
   6  import argparse
   7  import bisect
   8  import csv
   9  import hashlib
  10  import io
  11  import json
  12  import math
  13  import sys
  14  import urllib.error
  15  import urllib.request
  16  import zipfile
  17  from datetime import date, datetime, timedelta, timezone
  18  from pathlib import Path
  19  
  20  ASSETS = ("BTCUSDT", "ETHUSDT", "XRPUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "DOGEUSDT", "LTCUSDT")
  21  FIRST_MONTH = (2020, 8)
  22  LAST_MONTH = (2026, 10)
  23  FEE, SLIP = 0.00095, 0.0002
  24  COST_MULTIPLIERS = (1, 2, 3)
  25  GRID = [(w, h) for w in (7, 14) for h in (7, 14)]  # (W okno fundingu, H držení) ve dnech
  26  PERIODS = {"tuning": ("2020-10-05", "2022-12-31"),
  27             "validation": ("2023-01-01", "2024-12-31"),
  28             "final_test": ("2025-01-01", "2026-10-31")}
  29  WF_YEARS = (2021, 2022, 2023, 2024)
  30  START_EQUITY = 10_000.0
  31  LEG_FRACTION = 0.10
  32  N_SIDE = 2
  33  MIN_ELIGIBLE = 6
  34  FALLBACK_HOURS = 6
  35  DSR_N, DSR_VAR_ANNUAL = 159, 0.5
  36  HOUR_MS = 3_600_000
  37  DAY_MS = 86_400_000
  38  
  39  
  40  def vt(w, h):
  41      return f"W{w}_H{h}"
  42  
  43  
  44  # ------------------------------------------------------------------ data
  45  def months():
  46      y, m = FIRST_MONTH
  47      while (y, m) <= LAST_MONTH:
  48          yield y, m
  49          y, m = (y + 1, 1) if m == 12 else (y, m + 1)
  50  
  51  
  52  def fetch(url):
  53      req = urllib.request.Request(url, headers={"User-Agent": "paper-research/1.0"})
  54      with urllib.request.urlopen(req, timeout=90) as r:
  55          return r.read()
  56  
  57  
  58  def _csv_rows(payload):
  59      with zipfile.ZipFile(io.BytesIO(payload)) as z:
  60          text = z.read(z.namelist()[0]).decode()
  61      return [r for r in csv.reader(io.StringIO(text)) if r and r[0].strip().isdigit()]
  62  
  63  
  64  def _ms(ts):
  65      return ts // 1000 if ts > 10 ** 14 else ts
  66  
  67  
  68  def parse_klines(payload):
  69      return [(_ms(int(r[0])), float(r[1]), float(r[2]), float(r[3]), float(r[4])) for r in _csv_rows(payload)]
  70  
  71  
  72  def normalize_funding_ts(ts):
  73      """Na celou hodinu jen při odchylce ≤ 1 s (konvence repozitáře), jinak chyba."""
  74      near = round(ts / HOUR_MS) * HOUR_MS
  75      if abs(ts - near) > 1000:
  76          raise ValueError(f"funding timestamp {ts} je {ts - near} ms od celé hodiny")
  77      return near
  78  
  79  
  80  def parse_funding(payload):
  81      """Binance Vision fundingRate: calc_time, funding_interval_hours, last_funding_rate.
  82      → [(normalizovaný čas vypořádání, sazba, interval_h, surový calc_time)]"""
  83      out = []
  84      for r in _csv_rows(payload):
  85          raw = _ms(int(r[0]))
  86          out.append((normalize_funding_ts(raw), float(r[2]), float(r[1]), raw))
  87      return out
  88  
  89  
  90  def urls(asset):
  91      base = "https://data.binance.vision/data/futures/um/monthly"
  92      for y, m in months():
  93          tag = f"{y}-{m:02d}"
  94          yield "kl", (y, m), f"{base}/klines/{asset}/1h/{asset}-1h-{tag}.zip"
  95          yield "fr", (y, m), f"{base}/fundingRate/{asset}/{asset}-fundingRate-{tag}.zip"
  96  
  97  
  98  def add_funding(store, rows, asset, audit):
  99      """Oprava R1: duplicita po normalizaci se stejnou sazbou = počítat; s jinou sazbou nebo intervalem = chyba."""
 100      for ts, rate, interval_h, raw in rows:
 101          if ts in store:
 102              if store[ts][:2] != (rate, interval_h):
 103                  raise ValueError(f"konfliktní duplicitní funding {asset} {ts}: {store[ts][:2]} vs {(rate, interval_h)}")
 104              audit["duplicates_same_value"] += 1
 105              continue
 106          store[ts] = (rate, interval_h, raw)
 107  
 108  
 109  def load(cache, fetcher=fetch):
 110      market, manifest, missing, fatal = {}, [], [], []
 111      for a in ASSETS:
 112          bars, fund, present = {}, {}, {"kl": [], "fr": []}
 113          miss = {"kl": [], "fr": []}
 114          audit = {"duplicates_same_value": 0}
 115          for kind, ym, url in urls(a):
 116              p = Path(cache) / kind / url.rsplit("/", 1)[1]
 117              if not p.exists():
 118                  try:
 119                      payload = fetcher(url)
 120                  except urllib.error.HTTPError as e:
 121                      missing.append({"url": url, "http": e.code})
 122                      miss[kind].append(ym)
 123                      continue
 124                  p.parent.mkdir(parents=True, exist_ok=True)
 125                  p.write_bytes(payload)
 126              payload = p.read_bytes()
 127              present[kind].append(ym)
 128              if kind == "kl":
 129                  rows = parse_klines(payload)
 130                  for r in rows:
 131                      bars[r[0]] = r[1:]
 132              else:
 133                  rows = parse_funding(payload)
 134                  add_funding(fund, rows, a, audit)
 135              manifest.append({"url": url, "sha256": hashlib.sha256(payload).hexdigest(), "rows": len(rows)})
 136          for kind in ("kl", "fr"):
 137              # povolené jsou jen chybějící měsíce PŘED prvním existujícím (kontrakt ještě neobchodoval)
 138              if present[kind]:
 139                  first = min(present[kind])
 140                  fatal += [{"asset": a, "kind": kind, "month": f"{y}-{m:02d}"} for (y, m) in miss[kind] if (y, m) > first]
 141              else:
 142                  fatal.append({"asset": a, "kind": kind, "month": "all"})
 143          market[a] = prepare(bars, fund)
 144          market[a]["load_audit"] = audit
 145      return market, manifest, missing, fatal
 146  
 147  
 148  def prepare(bars, fund):
 149      """bars {ts: (o, h, l, c)}, fund {ts: rate | (rate, interval_h[, raw_ts])} → indexy pro kauzální dotazy.
 150      Holá sazba (syntetické testy) = interval 8 h, raw = ts."""
 151      norm = {}
 152      for ts, v in fund.items():
 153          if isinstance(v, tuple):
 154              norm[ts] = (v[0], v[1], v[2] if len(v) > 2 else ts)
 155          else:
 156              norm[ts] = (v, 8.0, ts)
 157      fts = sorted(norm)
 158      funding = {ts: norm[ts][0] for ts in fts}
 159      cum = [0.0]
 160      for ts in fts:
 161          cum.append(cum[-1] + funding[ts])
 162      return {"bars": bars, "bts": sorted(bars), "funding": funding, "finterval": {ts: norm[ts][1] for ts in fts},
 163              "fraw": {ts: norm[ts][2] for ts in fts}, "fts": fts, "fcum": cum,
 164              "first_bar": min(bars) if bars else None, "first_funding": fts[0] if fts else None}
 165  
 166  
 167  # ------------------------------------------------------------------ simulace
 168  def ms_of(d):
 169      return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)
 170  
 171  
 172  def date_of(ms):
 173      return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date()
 174  
 175  
 176  def first_monday_on_or_after(d):
 177      return d + timedelta(days=(7 - d.weekday()) % 7)
 178  
 179  
 180  FALLBACK_PURPOSES = ("entry", "exit", "funding", "liquidation_check", "mtm", "benchmark")
 181  
 182  
 183  class Prices:
 184      def __init__(self, market):
 185          self.m = market
 186          self.fallbacks = {p: 0 for p in FALLBACK_PURPOSES}
 187          self.last_fallback = False
 188  
 189      def get(self, a, t, field, purpose):
 190          """field: 0 open, 1 high, 2 low, 3 close. Chybí-li svíčka v t: close nejbližší dřívější do 6 h (dodatek 0);
 191          náhrada se počítá podle účelu (dodatek 2) — je to náhradní ocenění, ne důkaz realizovatelné ceny."""
 192          self.last_fallback = False
 193          b = self.m[a]["bars"].get(t)
 194          if b is not None:
 195              return b[field]
 196          for k in range(1, FALLBACK_HOURS + 1):
 197              b = self.m[a]["bars"].get(t - k * HOUR_MS)
 198              if b is not None:
 199                  self.fallbacks[purpose] += 1
 200                  self.last_fallback = True
 201                  return b[3]
 202          raise KeyError(f"chybí cena {a} {datetime.fromtimestamp(t / 1000, tz=timezone.utc)}")
 203  
 204  
 205  def decision_time(D):
 206      """Dodatek 2 (D): rozhodnutí až po zveřejnění sazby vypořádané v D (calc_time ≤ D + 1 s podle normalizace)."""
 207      return D + 1000
 208  
 209  
 210  def funding_signal(m, D, W):
 211      """Součet sazeb s časem vypořádání v (D − W dní, D] a surovým calc_time ≤ decision_time(D)."""
 212      lo = D - W * DAY_MS
 213      i, j = bisect.bisect_right(m["fts"], lo), bisect.bisect_right(m["fts"], D)
 214      assert all(m["fraw"][ts] <= decision_time(D) for ts in m["fts"][i:j])
 215      return m["fcum"][j] - m["fcum"][i]
 216  
 217  
 218  def funding_chain_gaps(m, lo, hi):
 219      """Počet nesouvislostí funding řady pokrývající (lo, hi]: chybí předchozí událost ≤ lo, rozestup dvou po sobě
 220      jdoucích událostí ≠ intervalu (podle intervalu té dřívější), nebo po poslední události ≤ hi chybí další před hi."""
 221      fts = m["fts"]
 222      i = bisect.bisect_right(fts, lo) - 1
 223      if i < 0:
 224          return None  # kontrakt ještě neměl funding
 225      gaps, k = 0, i
 226      while k + 1 < len(fts) and fts[k + 1] <= hi:
 227          if fts[k + 1] - fts[k] != m["finterval"][fts[k]] * HOUR_MS:
 228              gaps += 1
 229          k += 1
 230      if fts[k] + m["finterval"][fts[k]] * HOUR_MS <= hi and (k + 1 >= len(fts) or fts[k + 1] > hi):
 231          gaps += 1  # očekávaná událost ≤ hi chybí
 232      return gaps
 233  
 234  
 235  def price_gaps(m, lo, hi):
 236      """Počet chybějících hodinových svíček v [lo, hi]."""
 237      i, j = bisect.bisect_left(m["bts"], lo), bisect.bisect_right(m["bts"], hi)
 238      return (hi - lo) // HOUR_MS + 1 - (j - i)
 239  
 240  
 241  def eligibility(market, a, D, W, entry_ts=None):
 242      """Způsobilost jen z informací známých v D (dodatek 3): listing, všechny 1h svíčky UZAVŘENÉ do D ([D − W, D − 1 h])
 243      a souvislá funding řada (D − W, D]. Existence budoucí vstupní svíčky výběr neovlivňuje (kontroluje se až při vstupu).
 244      Chybějící funding se nikdy nepovažuje za nulový. Vrací (způsobilé, důvod). entry_ts je jen kvůli zpětné kompatibilitě."""
 245      m = market[a]
 246      if m["first_funding"] is None or m["first_bar"] is None:
 247          return False, "no_data"
 248      lo = D - W * DAY_MS
 249      if m["first_bar"] > lo or m["first_funding"] > lo:
 250          return False, "not_listed_for_window"
 251      if price_gaps(m, lo, D - HOUR_MS):
 252          return False, "price_gap_in_window"
 253      g = funding_chain_gaps(m, lo, D)
 254      if g is None or g > 0:
 255          return False, "funding_gap_in_window"
 256      return True, "ok"
 257  
 258  
 259  def eligible(market, a, D, W, entry_ts):
 260      return eligibility(market, a, D, W, entry_ts)[0]
 261  
 262  
 263  def select_legs(signals):
 264      order = sorted(signals.items(), key=lambda kv: (kv[1], kv[0]))
 265      longs = [a for a, _ in order[:N_SIDE]]
 266      shorts = [a for a, _ in order[-N_SIDE:]]
 267      return longs, shorts
 268  
 269  
 270  def _liquidate(lg, t, price):
 271      lg.update(alive=False, liquidated=1, exit_ts=t, exit=price, gross=-lg["notional"])
 272  
 273  
 274  def simulate(market, start, end, W, H, mult, variant="", prices=None):
 275      """Vrací (nohy, denní equity {date: value}, rozhodnutí).
 276      Pořadí v hodině t (vstup ≤ t < výstup): funding události v t (jen t > vstup) → kontrola likvidace short nohy
 277      podle high svíčky t → ocenění v 23:00. Ve výstupní hodině: je-li open ≥ 2 × vstup ⇒ likvidace gapem (ztráta =
 278      notional), jinak výstup za open. High po čase výstupu se nepoužívá (oprava R3)."""
 279      px = prices or Prices(market)
 280      c = (FEE + SLIP) * mult
 281      end_ms = ms_of(end) + DAY_MS
 282      D = ms_of(first_monday_on_or_after(start))
 283      first_decision = D
 284      cash = START_EQUITY
 285      legs, curve, decisions = [], {}, []
 286      while True:
 287          entry_ts, exit_ts = D + HOUR_MS, D + H * DAY_MS + HOUR_MS
 288          if exit_ts > end_ms - HOUR_MS:  # výstupní svíčka musí ležet v období
 289              break
 290          why = {a: eligibility(market, a, D, W, entry_ts)[1] for a in ASSETS}
 291          elig = [a for a in ASSETS if why[a] == "ok"]
 292          if len(elig) < MIN_ELIGIBLE:
 293              decisions.append({"decision_utc": datetime.fromtimestamp(decision_time(D) / 1000, tz=timezone.utc).isoformat(),
 294                                "decision": date_of(D).isoformat(), "skipped": True, "eligible": len(elig),
 295                                "ineligible_reasons": {a: r for a, r in why.items() if r != "ok"}})
 296              for k in range(7):
 297                  curve[date_of(D + k * DAY_MS)] = cash
 298              D += 7 * DAY_MS
 299              continue
 300          sig = {a: funding_signal(market[a], D, W) for a in elig}
 301          longs, shorts = select_legs(sig)
 302          decisions.append({"decision_utc": datetime.fromtimestamp(decision_time(D) / 1000, tz=timezone.utc).isoformat(),
 303                            "decision": date_of(D).isoformat(), "skipped": False, "eligible": len(elig),
 304                            "ineligible_reasons": {a: r for a, r in why.items() if r != "ok"},
 305                            "longs": longs, "shorts": shorts, "signal": sig})
 306          equity0 = cash
 307          open_legs = []
 308          basket_id = len(decisions)
 309          decisions[-1]["unfilled_legs"] = []
 310          for side, names in ((1, longs), (-1, shorts)):
 311              for a in names:
 312                  if entry_ts not in market[a]["bars"]:
 313                      # dodatek 3: chybí vstupní svíčka ⇒ noha se neotevře (slot zůstane v hotovosti), žádné přerankování
 314                      decisions[-1]["unfilled_legs"].append(a)
 315                      continue
 316                  e = px.get(a, entry_ts, 0, "entry")
 317                  notional = LEG_FRACTION * equity0
 318                  cost_in = notional * c
 319                  cash -= cost_in
 320                  open_legs.append({"period_variant": variant, "basket": basket_id, "asset": a, "side": side,
 321                                    "entry_ts": entry_ts, "entry": e, "qty": notional / e, "notional": notional,
 322                                    "costs": cost_in, "funding": 0.0, "liquidated": 0, "alive": True, "signal": sig[a],
 323                                    "price_fallbacks": 0,
 324                                    "funding_gaps_in_holding": funding_chain_gaps(market[a], entry_ts, exit_ts - 1) or 0})
 325          t = entry_ts
 326          while t < exit_ts:
 327              for lg in open_legs:
 328                  if not lg["alive"]:
 329                      continue
 330                  a = lg["asset"]
 331                  if t > entry_ts and t in market[a]["funding"]:
 332                      amt = -lg["side"] * market[a]["funding"][t] * lg["qty"] * px.get(a, t, 0, "funding")
 333                      lg["funding"] += amt
 334                  if lg["side"] == -1:
 335                      hi = px.get(a, t, 1, "liquidation_check")
 336                      lg["price_fallbacks"] += px.last_fallback
 337                      if hi >= 2 * lg["entry"]:
 338                          _liquidate(lg, t, 2 * lg["entry"])
 339                          cash += lg["gross"] + lg["funding"]
 340              if (t // HOUR_MS) % 24 == 23:  # close svíčky 23:00 = konec dne
 341                  mtm = sum(lg["side"] * lg["qty"] * (px.get(lg["asset"], t, 3, "mtm") - lg["entry"]) + lg["funding"]
 342                            for lg in open_legs if lg["alive"])
 343                  curve[date_of(t)] = cash + mtm
 344              t += HOUR_MS
 345          for lg in open_legs:
 346              if lg["alive"]:
 347                  x = px.get(lg["asset"], exit_ts, 0, "exit")
 348                  lg["price_fallbacks"] += px.last_fallback
 349                  if lg["side"] == -1 and x >= 2 * lg["entry"]:  # gap přes likvidační cenu ve výstupní hodině
 350                      _liquidate(lg, exit_ts, x)
 351                      cash += lg["gross"] + lg["funding"]
 352                  else:
 353                      cost_out = lg["qty"] * x * c
 354                      lg.update(alive=False, exit_ts=exit_ts, exit=x, gross=lg["side"] * lg["qty"] * (x - lg["entry"]))
 355                      lg["costs"] += cost_out
 356                      cash += lg["gross"] + lg["funding"] - cost_out
 357              lg["net_pnl"] = lg["gross"] + lg["funding"] - lg["costs"]
 358              legs.append(lg)
 359          D += H * DAY_MS
 360      # dny bez otevřeného koše (začátek, přeskočené týdny, konec) = hotovost
 361      # (po konci smyčky jsou všechny nohy uzavřené ⇒ zbylé dny = hotovost)
 362      full, d = {}, start
 363      while d <= end:
 364          full[d] = curve.get(d, START_EQUITY if ms_of(d) < first_decision else cash)
 365          d += timedelta(days=1)
 366      return legs, full, decisions
 367  
 368  
 369  # ------------------------------------------------------------------ metriky
 370  def curve_metrics(curve, start_value):
 371      vals = [curve[d] for d in sorted(curve)]
 372      rets = [vals[0] / start_value - 1] + [vals[k] / vals[k - 1] - 1 for k in range(1, len(vals))]
 373      mu = sum(rets) / len(rets)
 374      sd = math.sqrt(sum((r - mu) ** 2 for r in rets) / (len(rets) - 1)) if len(rets) > 1 else 0.0
 375      peak, mdd = start_value, 0.0
 376      for v in vals:
 377          peak = max(peak, v)
 378          mdd = max(mdd, 1 - v / peak)
 379      return {"return_pct": round((vals[-1] / start_value - 1) * 100, 4),
 380              "sharpe": round(mu / sd * math.sqrt(365), 4) if sd > 0 else 0.0,
 381              "max_drawdown_pct": round(mdd * 100, 4)}, rets
 382  
 383  
 384  def trade_metrics(legs):
 385      pnl = [lg["net_pnl"] for lg in legs]
 386      gains = sum(p for p in pnl if p > 0)
 387      losses = -sum(p for p in pnl if p < 0)
 388      top3 = sum(sorted(pnl, reverse=True)[:3])
 389      return {"trades": len(pnl), "net_pnl": round(sum(pnl), 4),
 390              "profit_factor": round(gains / losses, 4) if losses > 0 else (None if gains == 0 else 999.0),
 391              "net_without_top3": round(sum(pnl) - top3, 4),
 392              "funding": round(sum(lg["funding"] for lg in legs), 4),
 393              "costs": round(sum(lg["costs"] for lg in legs), 4),
 394              "liquidations": sum(lg["liquidated"] for lg in legs),
 395              "long_net": round(sum(lg["net_pnl"] for lg in legs if lg["side"] == 1), 4),
 396              "short_net": round(sum(lg["net_pnl"] for lg in legs if lg["side"] == -1), 4)}
 397  
 398  
 399  def run(market, start, end, mult, W, H, variant, prices=None):
 400      legs, curve, dec = simulate(market, start, end, W, H, mult, variant, prices)
 401      cm, rets = curve_metrics(curve, START_EQUITY)
 402      return {**cm, **trade_metrics(legs), "baskets": sum(1 for x in dec if not x["skipped"]),
 403              "skipped_weeks": sum(1 for x in dec if x["skipped"]),
 404              "edge_funding_events_excluded": simulate_edge_events(market, legs),
 405              "edge_funding_impact_abs_upper_bound": simulate_edge_events(market, legs, True)[1],
 406              "legs_with_price_fallback": sum(1 for lg in legs if lg["price_fallbacks"]),
 407              "legs_with_funding_gap_in_holding": sum(1 for lg in legs if lg["funding_gaps_in_holding"]),
 408              "per_basket": basket_metrics(legs),
 409              "unfilled_entry_legs": sum(len(x.get("unfilled_legs", [])) for x in dec)}, legs, rets, curve
 410  
 411  
 412  def buy_hold(market, start, end, mult, prices=None):
 413      """Oprava R2: B&H 8 perpů (long 12,5 % na aktivum, 1× bez páky, marže = notional) včetně skutečného fundingu:
 414      long platí kladnou sazbu z qty × open svíčky v čase události, pro události v (start 00:00, konec dne end).
 415      Nákup za open první hodiny, prodej za close svíčky 23:00 posledního dne; nedostupné aktivum = hotovost."""
 416      px = prices or Prices(market)
 417      c = (FEE + SLIP) * mult
 418      t0 = ms_of(start)
 419      t_end = ms_of(end) + 23 * HOUR_MS
 420      share = START_EQUITY / len(ASSETS)
 421      qty, cash, funding = {}, 0.0, 0.0
 422      for a in ASSETS:
 423          if t0 in market[a]["bars"]:
 424              qty[a] = share * (1 - c) / px.get(a, t0, 0, "benchmark")
 425          else:
 426              cash += share
 427      events = sorted((t, a) for a in qty for t in market[a]["fts"] if t0 < t <= t_end)
 428      k, curve, d = 0, {}, start
 429      while d <= end:
 430          t = ms_of(d) + 23 * HOUR_MS
 431          while k < len(events) and events[k][0] <= t:
 432              te, a = events[k]
 433              funding -= market[a]["funding"][te] * qty[a] * px.get(a, te, 0, "benchmark")
 434              k += 1
 435          curve[d] = cash + funding + sum(q * px.get(a, t, 3, "benchmark") for a, q in qty.items())
 436          d += timedelta(days=1)
 437      asset_value = curve[end] - cash - funding
 438      curve[end] = cash + funding + asset_value * (1 - c)
 439      cm, rets = curve_metrics(curve, START_EQUITY)
 440      return {**cm, "net_pnl": round(curve[end] - START_EQUITY, 4), "funding": round(funding, 4)}, rets
 441  
 442  
 443  def simulate_edge_events(market, legs, with_impact=False):
 444      """Funding události přesně v čase vstupu/výstupu nohy — podle protokolu se nezapočítají (dodatek 1).
 445      with_impact: (počet, součet |sazba × qty × cena|) = horní mez dopadu na P/L (dodatek 2, E)."""
 446      n, impact = 0, 0.0
 447      for lg in legs:
 448          m = market[lg["asset"]]
 449          for t, p in ((lg["entry_ts"], lg["entry"]), (lg["exit_ts"], lg["exit"])):
 450              if t in m["funding"]:
 451                  n += 1
 452                  impact += abs(m["funding"][t] * lg["qty"] * p)
 453      return (n, round(impact, 6)) if with_impact else n
 454  
 455  
 456  def basket_metrics(legs):
 457      """Dodatek 2 (B): metriky z celých košů (4 nohy jednoho rozhodnutí nejsou 4 nezávislá rozhodnutí)."""
 458      by = {}
 459      for lg in legs:
 460          by.setdefault(lg["basket"], []).append(lg)
 461      pnl = [sum(x["net_pnl"] for x in b) for _, b in sorted(by.items())]
 462      gains = sum(x for x in pnl if x > 0)
 463      losses = -sum(x for x in pnl if x < 0)
 464      return {"baskets": len(pnl), "net_pnl": round(sum(pnl), 4),
 465              "profit_factor": round(gains / losses, 4) if losses > 0 else (None if gains == 0 else 999.0),
 466              "net_without_top3": round(sum(pnl) - sum(sorted(pnl, reverse=True)[:3]), 4),
 467              "baskets_with_price_fallback": sum(1 for _, b in by.items() if any(x["price_fallbacks"] for x in b)),
 468              "baskets_with_funding_gap": sum(1 for _, b in by.items() if any(x["funding_gaps_in_holding"] for x in b))}
 469  
 470  
 471  def vol_matched(strategy_rets, bh_rets):
 472      """Info (dodatek 1): B&H přeškálované na stejnou denní volatilitu jako strategie (bez nákladů); kritéria nemění.
 473      EX-POST diagnostika (škála z celého období), ne obchodovatelný benchmark (dodatek 2, F)."""
 474      def sd(x):
 475          if len(x) < 2:
 476              return 0.0
 477          mu = sum(x) / len(x)
 478          return math.sqrt(sum((r - mu) ** 2 for r in x) / (len(x) - 1))
 479      k = sd(strategy_rets) / sd(bh_rets) if sd(bh_rets) > 0 else 0.0
 480      v, peak, mdd = 1.0, 1.0, 0.0
 481      for r in bh_rets:
 482          v *= 1 + k * r
 483          peak = max(peak, v)
 484          mdd = max(mdd, 1 - v / peak)
 485      return {"kind": "ex_post_diagnostic", "scale": round(k, 6), "return_pct": round((v - 1) * 100, 4), "max_drawdown_pct": round(mdd * 100, 4)}
 486  
 487  
 488  def corr(x, y):
 489      n = min(len(x), len(y))
 490      x, y = x[:n], y[:n]
 491      mx, my = sum(x) / n, sum(y) / n
 492      sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
 493      sx = math.sqrt(sum((a - mx) ** 2 for a in x))
 494      sy = math.sqrt(sum((b - my) ** 2 for b in y))
 495      return round(sxy / (sx * sy), 4) if sx > 0 and sy > 0 else None
 496  
 497  
 498  def btc_daily_returns(market, start, end, prices):
 499      vals, d = [], start - timedelta(days=1)
 500      while d <= end:
 501          vals.append(prices.get("BTCUSDT", ms_of(d) + 23 * HOUR_MS, 3, "benchmark"))
 502          d += timedelta(days=1)
 503      return [vals[k] / vals[k - 1] - 1 for k in range(1, len(vals))]
 504  
 505  
 506  def evaluate(res, bh):
 507      v1, v2 = res["validation"]["x1"], res["validation"]["x2"]
 508      f2, t1 = res["final_test"]["x2"], res["tuning"]["x1"]
 509      bv, bf = bh["validation"]["x1"], bh["final_test"]["x2"]
 510      a = {"A1_sharpe_dd": v1["sharpe"] > bv["sharpe"] and v1["max_drawdown_pct"] < bv["max_drawdown_pct"],
 511           "A2_trades_ge_30": v1["trades"] >= 30,
 512           "A3_x2_pf_profit": (v2["profit_factor"] or 0) > 1.2 and v2["net_pnl"] > 0,
 513           "A4_wo_top3": v1["net_without_top3"] > 0,
 514           "A5_final_x2": f2["net_pnl"] > 0 and f2["sharpe"] > bf["sharpe"]
 515           and f2["max_drawdown_pct"] < bf["max_drawdown_pct"]}
 516      b = {"B1_val_x2_profit_pf": v2["net_pnl"] > 0 and (v2["profit_factor"] or 0) > 1.2,
 517           "B2_dd_le_0_6_bh": v1["max_drawdown_pct"] <= 0.6 * bv["max_drawdown_pct"]
 518           and res["final_test"]["x1"]["max_drawdown_pct"] <= 0.6 * bh["final_test"]["x1"]["max_drawdown_pct"],
 519           "B3_final_x2_profit": f2["net_pnl"] > 0,
 520           "B4_val_wo_top3": v1["net_without_top3"] > 0,
 521           "B5_trades_ge_20": v1["trades"] + res["final_test"]["x1"]["trades"] >= 20,
 522           "B6_tuning_x1_profit": t1["net_pnl"] > 0}
 523      return a, b
 524  
 525  
 526  def data_audit(market):
 527      """Kontrola dat oddělená od výkonnosti (dodatek 3): všechny přechody funding_interval_hours s okolními časy a počet
 528      nesouladů rozestupu pro dvě možné sémantiky pole — A: interval platí od dané události k další (předpoklad kódu),
 529      B: interval popisuje úsek končící danou událostí. Sémantiku rozhodne člověk z konkrétních přechodů, ne kód."""
 530      out = {}
 531      for a in ASSETS:
 532          m = market[a]
 533          fts = m["fts"]
 534          trans, mis_a, mis_b = [], 0, 0
 535          for k in range(len(fts) - 1):
 536              sp = (fts[k + 1] - fts[k]) / HOUR_MS
 537              ia, ib = m["finterval"][fts[k]], m["finterval"][fts[k + 1]]
 538              mis_a += sp != ia
 539              mis_b += sp != ib
 540              if ia != ib:
 541                  ctx = [(datetime.fromtimestamp(fts[j] / 1000, tz=timezone.utc).isoformat(), m["finterval"][fts[j]])
 542                         for j in range(max(0, k - 2), min(len(fts), k + 4))]
 543                  trans.append({"at": datetime.fromtimestamp(fts[k + 1] / 1000, tz=timezone.utc).isoformat(),
 544                                "from_h": ia, "to_h": ib, "spacing_h": sp, "context": ctx})
 545          out[a] = {"funding_events": len(fts), "interval_transitions": trans,
 546                    "spacing_mismatch_semantics_A": mis_a, "spacing_mismatch_semantics_B": mis_b,
 547                    "hour_bars": len(m["bts"]),
 548                    "missing_hours_since_listing": (price_gaps(m, m["first_bar"], m["bts"][-1]) if m["bts"] else None),
 549                    "load_audit": m.get("load_audit")}
 550      return out
 551  
 552  
 553  def safe_dsr(rets, n, var_annual):
 554      """Oprava R4: nedefinované DSR (nulový rozptyl, např. žádné obchody) = None + důvod, brána neprošla."""
 555      sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
 556      from tools.research.deflated_sharpe import dsr_from_returns
 557      try:
 558          return {**dsr_from_returns(rets, n, var_annual / 365), "undefined_reason": None}
 559      except (ValueError, ZeroDivisionError) as e:
 560          return {"dsr": None, "undefined_reason": str(e), "n_trials": n, "var_trials": var_annual / 365}
 561  
 562  
 563  DSR_SENSITIVITY_N = (159, 318, 636)
 564  DSR_SENSITIVITY_V = (0.5, 1.0, 2.0)
 565  
 566  
 567  def neighbors(w, h):
 568      return [(w2, h2) for (w2, h2) in GRID if (w2 == w) != (h2 == h)]
 569  
 570  
 571  def pdate(s):
 572      return date.fromisoformat(s)
 573  
 574  
 575  def leg_row(period, mult, lg):
 576      return {"period": period, "variant": lg["period_variant"], "cost_mult": mult, "asset": lg["asset"],
 577              "side": "LONG" if lg["side"] == 1 else "SHORT", "signal_funding_sum": round(lg["signal"], 8),
 578              "entry_utc": datetime.fromtimestamp(lg["entry_ts"] / 1000, tz=timezone.utc).isoformat(),
 579              "exit_utc": datetime.fromtimestamp(lg["exit_ts"] / 1000, tz=timezone.utc).isoformat(),
 580              "entry": lg["entry"], "exit": lg["exit"], "qty": round(lg["qty"], 10),
 581              "notional": round(lg["notional"], 6), "gross": round(lg["gross"], 6),
 582              "funding": round(lg["funding"], 6), "costs": round(lg["costs"], 6),
 583              "liquidated": lg["liquidated"], "basket": lg["basket"], "price_fallbacks": lg["price_fallbacks"],
 584              "funding_gaps_in_holding": lg["funding_gaps_in_holding"], "net_pnl": round(lg["net_pnl"], 6)}
 585  
 586  
 587  def main(argv=None):
 588      ap = argparse.ArgumentParser()
 589      ap.add_argument("--cache", default="/tmp/vision-fd")
 590      ap.add_argument("--outdir", default="research/funding_dispersion")
 591      ap.add_argument("--audit-only", action="store_true", help="jen kontrola dat, bez výpočtu výkonnosti")
 592      args = ap.parse_args(argv)
 593      out = Path(args.outdir)
 594      market, manifest, missing, fatal = load(args.cache)
 595      (out / "data_source.json").write_text(json.dumps({"archives": manifest, "missing": missing}, indent=1))
 596      if fatal:
 597          print("FATAL missing archives after first available month", json.dumps(fatal[:30]))
 598          sys.exit(2)
 599      audit = data_audit(market)
 600      (out / "data_audit.json").write_text(json.dumps(audit, indent=1, default=str))
 601      print("DATA_AUDIT", json.dumps({a: {k: v for k, v in x.items() if k != "interval_transitions"} | {
 602          "interval_transitions": len(x["interval_transitions"])} for a, x in audit.items()}, default=str))
 603      if args.audit_only:
 604          return
 605      first_bar = {a: date_of(market[a]["first_bar"]).isoformat() if market[a]["first_bar"] else None for a in ASSETS}
 606      first_funding = {a: date_of(market[a]["first_funding"]).isoformat() if market[a]["first_funding"] else None
 607                       for a in ASSETS}
 608      print("DATA_COVERAGE", json.dumps({"first_bar": first_bar, "first_funding": first_funding}))
 609      px = Prices(market)
 610  
 611      rows, results, tune, rets_store = [], {}, {}, {}
 612      for (w, h) in GRID:
 613          tag = vt(w, h)
 614          results[tag] = {}
 615          for p, (s, e) in PERIODS.items():
 616              results[tag][p] = {}
 617              for m in COST_MULTIPLIERS:
 618                  r, legs, rets, _ = run(market, pdate(s), pdate(e), m, w, h, tag, px)
 619                  results[tag][p][f"x{m}"] = r
 620                  rets_store[(tag, p, m)] = rets
 621                  rows += [leg_row(p, m, lg) for lg in legs]
 622          tune[tag] = results[tag]["tuning"]["x1"]
 623      chosen = max(GRID, key=lambda g: (tune[vt(*g)]["net_pnl"], -GRID.index(g)))
 624      ctag = vt(*chosen)
 625      bh, bh_rets = {}, {}
 626      for p, (s, e) in PERIODS.items():
 627          bh[p] = {}
 628          for m in COST_MULTIPLIERS:
 629              bh[p][f"x{m}"], bh_rets[(p, m)] = buy_hold(market, pdate(s), pdate(e), m, px)
 630      wf = {}
 631      for y in WF_YEARS:
 632          r, legs, _, _ = run(market, date(y, 1, 1), date(y, 12, 31), 2, chosen[0], chosen[1], ctag, px)
 633          wf[str(y)] = r
 634          rows += [leg_row(f"wf_{y}", 2, lg) for lg in legs]
 635  
 636      res = results[ctag]
 637      track_a, track_b = evaluate(res, bh)
 638      passed_a, passed_b = all(track_a.values()), all(track_b.values())
 639      vrets = rets_store[(ctag, "validation", 1)]
 640      dsr = safe_dsr(vrets, DSR_N, DSR_VAR_ANNUAL)
 641      dsr_sens = {f"N{n}_V{v}": safe_dsr(vrets, n, v)["dsr"] for n in DSR_SENSITIVITY_N for v in DSR_SENSITIVITY_V}
 642      nb = {vt(*g): results[vt(*g)]["validation"]["x2"]["net_pnl"] for g in neighbors(*chosen)}
 643      wf_pos = sum(1 for y in wf.values() if y["net_pnl"] > 0)
 644      robust = {"dsr_ge_0_95": dsr["dsr"] is not None and dsr["dsr"] >= 0.95,
 645                "neighbors_val_x2_profit": all(v > 0 for v in nb.values()),
 646                "walk_forward_ge_3_of_4": wf_pos >= 3}
 647      s, e = PERIODS["validation"]
 648      beta_info = {"corr_daily_vs_btc_validation_x1": corr(rets_store[(ctag, "validation", 1)],
 649                                                           btc_daily_returns(market, pdate(s), pdate(e), px)),
 650                   "gross_exposure_strategy": 4 * LEG_FRACTION, "gross_exposure_bh": 1.0,
 651                   "bh_vol_matched_x1": {p: vol_matched(rets_store[(ctag, p, 1)], bh_rets[(p, 1)])
 652                                         for p in ("validation", "final_test")}}
 653      verdict = ("KANDIDÁT NA FORWARD PAPER" if (passed_a or passed_b) and all(robust.values()) else "ZAMÍTNUTO")
 654      flags = {"edge_funding_events": sum(res[p]["x1"]["edge_funding_events_excluded"] for p in PERIODS),
 655               "unfilled_entry_legs": sum(res[p]["x1"]["unfilled_entry_legs"] for p in PERIODS),
 656               "legs_with_price_fallback": sum(res[p]["x1"]["legs_with_price_fallback"] for p in PERIODS),
 657               "legs_with_funding_gap_in_holding": sum(res[p]["x1"]["legs_with_funding_gap_in_holding"] for p in PERIODS)}
 658      if verdict.startswith("KANDIDÁT") and any(flags.values()):
 659          verdict = "NEROZHODNUTO — výsledek ovlivněn hranami fundingu / mezerami dat, nutná revize (dodatek 2)"
 660      payload = {"protocol": "research/funding_dispersion/PROTOCOL.md", "chosen": ctag,
 661                 "tuning_selection_x1": tune, "strategy": results, "buy_hold_equal_8": bh,
 662                 "walk_forward_x2": wf,
 663                 "walk_forward_note": "roční stabilita fixní varianty vybrané na 2020-10…2022; pro 2021–22 NE čistý OOS walk-forward", "neighbors_val_x2": nb, "track_a": track_a, "track_b": track_b,
 664                 "passed_a": passed_a, "passed_b": passed_b, "dsr_validation_x1": dsr,
 665                 "dsr_note": "N = 159 je pracovní odhad (ne doložená horní mez); V[SR] = 0,5 p.a. je předpoklad",
 666                 "dsr_sensitivity_scenarios": dsr_sens, "robustness": robust, "interpretation_flags": flags,
 667                 "info": {**beta_info, "price_fallbacks_by_purpose": px.fallbacks, "first_bar": first_bar,
 668                          "first_funding": first_funding,
 669                          "load_audit": {a: market[a].get("load_audit") for a in ASSETS}},
 670                 "verdict": verdict}
 671      (out / "results.json").write_text(json.dumps(payload, indent=1, default=str))
 672      with open(out / "trades.csv", "w", newline="") as fh:
 673          w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["period"])
 674          w.writeheader()
 675          w.writerows(rows)
 676      print("SUMMARY", json.dumps({"chosen": ctag, "verdict": verdict, "track_a": track_a, "track_b": track_b,
 677                                   "robust": robust, "dsr": dsr["dsr"], "dsr_sens": dsr_sens, "flags": flags,
 678                                   "neighbors": nb,
 679                                   "val": res["validation"], "final": res["final_test"], "tuning": res["tuning"],
 680                                   "bh_val": bh["validation"]["x1"], "bh_final": bh["final_test"]["x2"],
 681                                   "wf": {k: v["net_pnl"] for k, v in wf.items()}, **beta_info,
 682                                   "fallbacks": px.fallbacks}, default=str))
 683  
 684  
 685  if __name__ == "__main__":
 686      main()
````

## C2. tests/test_funding_dispersion.py (`8a008b6`)
````python
   1  """Mechanika backtestu H-20261106-2 na syntetických datech (není důkaz ziskovosti)."""
   2  from datetime import date
   3  
   4  import pytest
   5  
   6  from research.funding_dispersion import run as fd
   7  
   8  H = fd.HOUR_MS
   9  DAY = fd.DAY_MS
  10  START = date(2021, 1, 4)  # pondělí
  11  
  12  
  13  def make_market(days=60, price=None, rates=None, start=date(2020, 12, 1)):
  14      """price(a, t) a rates(a, t) volitelné; výchozí cena 100, funding 0 po 8 h."""
  15      t0 = fd.ms_of(start)
  16      market = {}
  17      for k, a in enumerate(fd.ASSETS):
  18          bars, fund = {}, {}
  19          for i in range(days * 24):
  20              t = t0 + i * H
  21              p = price(a, t) if price else 100.0
  22              hi = p if not isinstance(p, tuple) else p[1]
  23              p = p if not isinstance(p, tuple) else p[0]
  24              bars[t] = (p, max(p, hi), p, p)
  25              if (t // H) % 8 == 0:
  26                  fund[t] = rates(a, t) if rates else 0.0
  27          market[a] = fd.prepare(bars, fund)
  28      return market
  29  
  30  
  31  def ranked_rates(a, t):
  32      return 0.0001 * fd.ASSETS.index(a)  # BTC nejnižší … LTC nejvyšší
  33  
  34  
  35  def test_selection_longs_lowest_shorts_highest():
  36      m = make_market(rates=ranked_rates)
  37      legs, _, dec = fd.simulate(m, START, date(2021, 1, 20), 7, 7, 1)
  38      d0 = dec[0]
  39      assert d0["longs"] == ["BTCUSDT", "ETHUSDT"]
  40      assert d0["shorts"] == ["DOGEUSDT", "LTCUSDT"]
  41      assert len(legs) == 8  # 2 koše × 4 nohy
  42  
  43  
  44  def test_signal_uses_only_settled_rates_up_to_decision():
  45      D = fd.ms_of(START)
  46      base = make_market(rates=lambda a, t: 0.001 if t > D else 0.0)
  47      assert fd.funding_signal(base["BTCUSDT"], D, 7) == 0.0
  48      # událost přesně v D (vypořádaná) se započte, D − 7 dní ne
  49      m = make_market(rates=lambda a, t: 1.0 if t in (D, D - 7 * DAY) else 0.0)
  50      assert fd.funding_signal(m["BTCUSDT"], D, 7) == pytest.approx(1.0)
  51  
  52  
  53  def test_prefix_invariance_of_decisions():
  54      m_long = make_market(days=80, rates=ranked_rates)
  55      m_short = make_market(days=50, rates=ranked_rates)
  56      _, _, d_long = fd.simulate(m_long, START, date(2021, 1, 18), 7, 7, 1)
  57      _, _, d_short = fd.simulate(m_short, START, date(2021, 1, 18), 7, 7, 1)
  58      assert d_long == d_short
  59  
  60  
  61  def test_funding_cashflow_sign_and_boundaries():
  62      D = fd.ms_of(START)
  63      entry, exit_ = D + H, D + 7 * DAY + H
  64      # kladná sazba jen v době držení; LTC (short) inkasuje, BTC (long) platí; hraniční události se nepočítají
  65      def rates(a, t):
  66          if t <= D:
  67              return ranked_rates(a, t)
  68          return 0.001 if entry < t < exit_ else 0.0
  69      m = make_market(rates=rates)
  70      legs, _, _ = fd.simulate(m, START, date(2021, 1, 11), 7, 7, 1)
  71      n_events = sum(1 for t in m["BTCUSDT"]["funding"] if entry < t < exit_)
  72      assert n_events == 21
  73      by = {lg["asset"]: lg for lg in legs}
  74      qty = by["BTCUSDT"]["qty"]
  75      assert by["BTCUSDT"]["funding"] == pytest.approx(-0.001 * qty * 100 * 21)
  76      assert by["LTCUSDT"]["funding"] == pytest.approx(0.001 * by["LTCUSDT"]["qty"] * 100 * 21)
  77  
  78  
  79  def test_costs_scale_linearly():
  80      m = make_market(rates=ranked_rates)
  81      res = {}
  82      for mult in (1, 2, 3):
  83          legs, _, _ = fd.simulate(m, START, date(2021, 1, 11), 7, 7, mult)
  84          res[mult] = sum(lg["costs"] for lg in legs)
  85      assert res[2] == pytest.approx(2 * res[1])
  86      assert res[3] == pytest.approx(3 * res[1])
  87      assert res[1] == pytest.approx(4 * 1000 * (fd.FEE + fd.SLIP) * 2)
  88  
  89  
  90  def test_short_leg_liquidation_at_double_price():
  91      D = fd.ms_of(START)
  92      def price(a, t):
  93          if a == "LTCUSDT" and t >= D + 3 * DAY:
  94              return (100.0, 250.0)
  95          return 100.0
  96      m = make_market(price=price, rates=ranked_rates)
  97      legs, _, _ = fd.simulate(m, START, date(2021, 1, 11), 7, 7, 1)
  98      ltc = [lg for lg in legs if lg["asset"] == "LTCUSDT"][0]
  99      assert ltc["liquidated"] == 1
 100      assert ltc["gross"] == pytest.approx(-ltc["notional"])
 101  
 102  
 103  def test_long_short_pnl_and_no_overlap():
 104      D = fd.ms_of(START)
 105      def price(a, t):
 106          if t <= D + H:
 107              return 100.0
 108          return 110.0 if a in ("BTCUSDT", "ETHUSDT") else 90.0
 109      m = make_market(price=price, rates=ranked_rates)
 110      legs, curve, _ = fd.simulate(m, START, date(2021, 1, 11), 7, 7, 1)
 111      first = [lg for lg in legs if lg["entry_ts"] == D + H]
 112      assert len(first) == 4
 113      for lg in first:
 114          assert lg["gross"] == pytest.approx(lg["notional"] * 0.10)  # long +10 %, short z poklesu 10 %
 115      ends = sorted((lg["entry_ts"], lg["exit_ts"]) for lg in legs)
 116      assert all(e <= s2 for (_, e), (s2, _) in zip(ends[::4], ends[4::4]))
 117      assert curve[date(2021, 1, 4)] > fd.START_EQUITY
 118  
 119  
 120  def test_skips_week_when_too_few_eligible():
 121      m = make_market(rates=ranked_rates)
 122      for a in fd.ASSETS[:3]:
 123          m[a] = fd.prepare({}, {})
 124      legs, curve, dec = fd.simulate(m, START, date(2021, 1, 20), 7, 7, 1)
 125      assert legs == [] and all(d["skipped"] for d in dec)
 126      assert set(curve.values()) == {fd.START_EQUITY}
 127  
 128  
 129  def test_buy_hold_and_evaluate_shapes():
 130      m = make_market(rates=ranked_rates)
 131      bh, rets = fd.buy_hold(m, START, date(2021, 1, 20), 1)
 132      assert bh["net_pnl"] < 0 and len(rets) == 17
 133      assert set(fd.neighbors(7, 7)) == {(7, 14), (14, 7)}
 134  
 135  
 136  # ---- regresní testy na žádost oponentury ChatGPT (DIALOG.md kolo 1) ----
 137  def _first_basket(legs, D):
 138      return sorted(((lg["asset"], lg["side"], lg["entry_ts"], lg["exit_ts"], round(lg["qty"], 9),
 139                      round(lg["funding"], 9), round(lg["net_pnl"], 9)) for lg in legs if lg["entry_ts"] == D + H))
 140  
 141  
 142  def test_funding_exactly_at_entry_and_exit_is_excluded():
 143      D = fd.ms_of(START)
 144      entry, exit_ = D + H, D + 7 * DAY + H
 145      m = make_market(rates=lambda a, t: ranked_rates(a, t) if t <= D else 0.0)
 146      for a in fd.ASSETS:  # nenulová sazba přesně na hranách (01:00) – nesmí se započíst
 147          f = dict(m[a]["funding"])
 148          f[entry] = f[exit_] = 0.05
 149          m[a] = fd.prepare(m[a]["bars"], f)
 150      legs, _, _ = fd.simulate(m, START, date(2021, 1, 11), 7, 7, 1)
 151      first = [lg for lg in legs if lg["entry_ts"] == entry]
 152      assert len(first) == 4 and all(lg["funding"] == 0.0 for lg in first)
 153      assert fd.simulate_edge_events(m, legs) == 8  # 4 nohy × (vstup + výstup), vykázáno informativně
 154  
 155  
 156  def test_funding_one_hour_inside_edges_is_included_once():
 157      D = fd.ms_of(START)
 158      entry, exit_ = D + H, D + 7 * DAY + H
 159      m = make_market(rates=lambda a, t: ranked_rates(a, t) if t <= D else 0.0)
 160      for a in fd.ASSETS:
 161          f = dict(m[a]["funding"])
 162          f[entry + H] = f[exit_ - H] = 0.001
 163          m[a] = fd.prepare(m[a]["bars"], f)
 164      legs, _, _ = fd.simulate(m, START, date(2021, 1, 11), 7, 7, 1)
 165      for lg in [x for x in legs if x["entry_ts"] == entry]:
 166          assert lg["funding"] == pytest.approx(-lg["side"] * 0.001 * lg["qty"] * 100 * 2)
 167  
 168  
 169  def test_changing_future_data_does_not_change_earlier_decisions_weights_fills():
 170      """Kauzalita: data po výstupu prvního koše se ZMĚNÍ (ne jen připojí) ⇒ 1. koš beze změny."""
 171      D = fd.ms_of(START)
 172      cut = D + 7 * DAY + H  # výstup 1. koše
 173      base = make_market(days=60, rates=ranked_rates)
 174      alt = make_market(days=60, price=lambda a, t: 100.0 if t <= cut else (300.0, 900.0),
 175                        rates=lambda a, t: ranked_rates(a, t) if t <= cut else (-1) ** fd.ASSETS.index(a) * 0.01)
 176      lb, _, db = fd.simulate(base, START, date(2021, 1, 25), 7, 7, 1)
 177      la, _, da = fd.simulate(alt, START, date(2021, 1, 25), 7, 7, 1)
 178      assert _first_basket(lb, D) == _first_basket(la, D)
 179      assert db[0] == da[0] and db[1] == da[1]  # 2. rozhodnutí (11. 1. 00:00) leží před změnou v 01:00
 180      assert db[2] != da[2]  # 3. rozhodnutí už vidí změněný funding ⇒ test má sílu
 181  
 182  
 183  def test_costs_charged_on_all_four_legs_entry_and_exit():
 184      m = make_market(rates=lambda a, t: 0.0001 * fd.ASSETS.index(a) if t <= fd.ms_of(START) else 0.0)
 185      legs, curve, _ = fd.simulate(m, START, date(2021, 1, 11), 7, 7, 1)
 186      c = fd.FEE + fd.SLIP
 187      assert len(legs) == 4
 188      for lg in legs:
 189          assert lg["costs"] == pytest.approx(2 * 1000 * c) and lg["net_pnl"] == pytest.approx(-2 * 1000 * c)
 190      assert curve[date(2021, 1, 11)] == pytest.approx(fd.START_EQUITY - 8 * 1000 * c)
 191  
 192  
 193  def test_vol_matched_benchmark_info():
 194      out = fd.vol_matched(strategy_rets=[0.01, -0.01] * 10, bh_rets=[0.04, -0.04] * 10)
 195      assert out["scale"] == pytest.approx(0.25)
 196      assert 0 < out["max_drawdown_pct"] < 2
 197  
 198  
 199  # ---- kolo 2 oponentury ChatGPT: R1–R4 a body B, D, E ----
 200  def test_R1_repro_sparse_data_is_not_eligible():
 201      D = fd.ms_of(START)
 202      m = {"BTCUSDT": fd.prepare({D - 20 * DAY: (1, 1, 1, 1), D + H: (1, 1, 1, 1)}, {D - 20 * DAY: 0.0})}
 203      ok, why = fd.eligibility(m, "BTCUSDT", D, 7, D + H)
 204      assert ok is False and why == "price_gap_in_window"
 205  
 206  
 207  def test_R1_missing_funding_event_inside_window_makes_ineligible_not_zero():
 208      D = fd.ms_of(START)
 209      m = make_market(rates=ranked_rates)
 210      a = "ETHUSDT"
 211      f = dict(m[a]["funding"])
 212      del f[D - 2 * DAY]  # vnitřní mezera
 213      m[a] = fd.prepare(m[a]["bars"], f)
 214      assert fd.eligibility(m, a, D, 7, D + H) == (False, "funding_gap_in_window")
 215      _, _, dec = fd.simulate(m, START, date(2021, 1, 11), 7, 7, 1)
 216      assert a not in dec[0]["signal"] and dec[0]["ineligible_reasons"] == {a: "funding_gap_in_window"}
 217  
 218  
 219  def test_R1_interval_change_8h_4h_1h_is_continuous():
 220      D = fd.ms_of(START)
 221      bars = {D - 10 * DAY + i * H: (100.0, 100.0, 100.0, 100.0) for i in range(12 * 24)}
 222      f, t = {}, D - 10 * DAY
 223      while t <= D + 3 * DAY:
 224          iv = 8 if t < D - 5 * DAY else (4 if t < D - 2 * DAY else 1)
 225          f[t] = (0.0001, float(iv))
 226          t += iv * H
 227      m = {"BTCUSDT": fd.prepare(bars, f)}
 228      assert fd.eligibility(m, "BTCUSDT", D, 7, D + H) == (True, "ok")
 229      # počet událostí v okně odpovídá intervalům: 8h do D−5 d, 4h do D−2 d, 1h do D
 230      assert fd.funding_signal(m["BTCUSDT"], D, 7) == pytest.approx(0.0001 * (6 + 18 + 48))
 231  
 232  
 233  def test_R1_duplicate_after_normalization():
 234      audit = {"duplicates_same_value": 0}
 235      store = {}
 236      fd.add_funding(store, [(0, 0.001, 8.0, 5), (0, 0.001, 8.0, 12)], "BTCUSDT", audit)
 237      assert audit["duplicates_same_value"] == 1 and len(store) == 1
 238      with pytest.raises(ValueError):
 239          fd.add_funding(store, [(0, 0.002, 8.0, 7)], "BTCUSDT", audit)
 240      with pytest.raises(ValueError):
 241          fd.normalize_funding_ts(3 * H + 1500)
 242  
 243  
 244  def test_R2_benchmark_accounts_funding_sign():
 245      res = {}
 246      for r in (0.0, 0.01, -0.01):
 247          mk = make_market(rates=lambda a, t, r=r: r)
 248          res[r] = fd.buy_hold(mk, START, date(2021, 1, 11), 1)[0]
 249      assert res[0.0]["net_pnl"] == pytest.approx(-22.9868, abs=1e-4)
 250      assert res[0.01]["net_pnl"] < res[0.0]["net_pnl"] < res[-0.01]["net_pnl"]
 251      # 8 dní × 3 události, každá 1 % z 9 988,5 notional (po vstupních nákladech); poslední den 00:00 je uvnitř
 252      n_events = sum(1 for t in mk["BTCUSDT"]["fts"] if fd.ms_of(START) < t <= fd.ms_of(date(2021, 1, 11)) + 23 * H)
 253      assert res[0.01]["funding"] == pytest.approx(-0.01 * fd.START_EQUITY * (1 - (fd.FEE + fd.SLIP)) * n_events)
 254  
 255  
 256  def test_R3_gap_through_liquidation_at_exit_open():
 257      D = fd.ms_of(START)
 258      exit_ = D + 7 * DAY + H
 259      def price(a, t):
 260          return 300.0 if a == "LTCUSDT" and t >= exit_ else 100.0
 261      m = make_market(price=price, rates=lambda a, t: ranked_rates(a, t) if t <= D else 0.0)
 262      legs, _, _ = fd.simulate(m, START, date(2021, 1, 11), 7, 7, 1)
 263      ltc = [lg for lg in legs if lg["asset"] == "LTCUSDT"][0]
 264      assert ltc["liquidated"] == 1 and ltc["gross"] == pytest.approx(-1000.0) and ltc["exit_ts"] == exit_
 265  
 266  
 267  def test_R3_high_of_exit_hour_is_not_used():
 268      D = fd.ms_of(START)
 269      exit_ = D + 7 * DAY + H
 270      def price(a, t):
 271          return (100.0, 500.0) if a == "LTCUSDT" and t == exit_ else 100.0  # open 100, high 500 až po výstupu
 272      m = make_market(price=price, rates=lambda a, t: ranked_rates(a, t) if t <= D else 0.0)
 273      legs, _, _ = fd.simulate(m, START, date(2021, 1, 11), 7, 7, 1)
 274      ltc = [lg for lg in legs if lg["asset"] == "LTCUSDT"][0]
 275      assert ltc["liquidated"] == 0 and ltc["gross"] == pytest.approx(0.0)
 276  
 277  
 278  def test_R4_no_trades_still_writes_results_with_null_dsr(tmp_path, monkeypatch):
 279      t0, t1 = fd.ms_of(date(2020, 9, 1)), fd.ms_of(date(2026, 11, 1))
 280      bars = {t: (100.0, 100.0, 100.0, 100.0) for t in range(t0, t1, H)}
 281      market = {a: fd.prepare(bars, {}) for a in fd.ASSETS}  # bez fundingu ⇒ nic není způsobilé
 282      for a in fd.ASSETS:
 283          market[a]["first_funding"] = None
 284      monkeypatch.setattr(fd, "load", lambda cache: (market, [], [], []))
 285      fd.main(["--outdir", str(tmp_path)])
 286      import json
 287      r = json.loads((tmp_path / "results.json").read_text())
 288      assert r["dsr_validation_x1"]["dsr"] is None and r["dsr_validation_x1"]["undefined_reason"]
 289      assert r["robustness"]["dsr_ge_0_95"] is False and r["verdict"] == "ZAMÍTNUTO"
 290      assert r["strategy"]["W7_H7"]["validation"]["x1"]["trades"] == 0
 291      assert set(r["dsr_sensitivity_scenarios"]) == {f"N{n}_V{v}" for n in (159, 318, 636) for v in (0.5, 1.0, 2.0)}
 292  
 293  
 294  def test_R4_constant_returns_dsr_undefined():
 295      out = fd.safe_dsr([0.0] * 731, 159, 0.5)
 296      assert out["dsr"] is None and "rozptyl" in out["undefined_reason"]
 297  
 298  
 299  def test_B_basket_metrics_aggregate_four_legs():
 300      m = make_market(rates=lambda a, t: ranked_rates(a, t) if t <= fd.ms_of(START) else 0.0)
 301      legs, _, _ = fd.simulate(m, START, date(2021, 1, 11), 7, 7, 1)
 302      b = fd.basket_metrics(legs)
 303      assert b["baskets"] == 1 and b["net_pnl"] == pytest.approx(sum(lg["net_pnl"] for lg in legs))
 304  
 305  
 306  def test_D_decision_after_publication_time():
 307      D = fd.ms_of(START)
 308      m = make_market(rates=ranked_rates)
 309      f = {t: (r, 8.0, t + 31 if t == D else t) for t, r in m["BTCUSDT"]["funding"].items()}  # calc_time D + 31 ms
 310      mk = fd.prepare(m["BTCUSDT"]["bars"], f)
 311      assert mk["fraw"][D] == D + 31 <= fd.decision_time(D)
 312      assert fd.funding_signal(mk, D, 7) == pytest.approx(0.0)  # BTC sazba 0 v ranked_rates
 313  
 314  
 315  def test_E_edge_funding_impact_is_quantified():
 316      D = fd.ms_of(START)
 317      entry = D + H
 318      m = make_market(rates=lambda a, t: ranked_rates(a, t) if t <= D else 0.0)
 319      for a in fd.ASSETS:
 320          f = dict(m[a]["funding"])
 321          f[entry] = 0.01
 322          m[a] = fd.prepare(m[a]["bars"], f)
 323      legs, _, _ = fd.simulate(m, START, date(2021, 1, 11), 7, 7, 1)
 324      n, impact = fd.simulate_edge_events(m, legs, True)
 325      assert n == 4 and impact == pytest.approx(4 * 0.01 * 1000)
 326  
 327  
 328  # ---- kolo 3 oponentury ChatGPT ----
 329  def test_K3_1_missing_future_entry_bar_does_not_change_selection():
 330      D = fd.ms_of(START)
 331      rates = lambda a, t: 0.0001 * ((fd.ASSETS.index(a) * 3) % 8)
 332      m = make_market(rates=rates)
 333      _, _, d0 = fd.simulate(m, START, date(2021, 1, 11), 7, 7, 1)
 334      gone = d0[0]["longs"][0]
 335      b = dict(m[gone]["bars"])
 336      del b[D + H]
 337      m[gone] = fd.prepare(b, m[gone]["funding"])
 338      legs, _, d1 = fd.simulate(m, START, date(2021, 1, 11), 7, 7, 1)
 339      assert d1[0]["signal"] == d0[0]["signal"]
 340      assert (d1[0]["longs"], d1[0]["shorts"]) == (d0[0]["longs"], d0[0]["shorts"])
 341      assert d1[0]["decision_utc"] == "2021-01-04T00:00:01+00:00"
 342      assert d1[0]["unfilled_legs"] == [gone] and gone not in {lg["asset"] for lg in legs}
 343      assert len(legs) == 3  # žádné přerankování, slot zůstal v hotovosti
 344  
 345  
 346  def test_K3_eligibility_uses_only_bars_closed_by_decision():
 347      D = fd.ms_of(START)
 348      m = make_market(rates=ranked_rates)
 349      b = dict(m["BTCUSDT"]["bars"])
 350      del b[D]  # svíčka 00:00–01:00 se uzavře až po rozhodnutí ⇒ nesmí ovlivnit způsobilost
 351      m["BTCUSDT"] = fd.prepare(b, m["BTCUSDT"]["funding"])
 352      assert fd.eligibility(m, "BTCUSDT", D, 7) == (True, "ok")
 353      del b[D - H]  # svíčka 23:00–24:00 uzavřená v D ⇒ mezera
 354      m["BTCUSDT"] = fd.prepare(b, m["BTCUSDT"]["funding"])
 355      assert fd.eligibility(m, "BTCUSDT", D, 7) == (False, "price_gap_in_window")
 356  
 357  
 358  def test_K3_data_audit_reports_interval_transitions_for_both_semantics():
 359      D = fd.ms_of(START)
 360      bars = {D - 10 * DAY + i * H: (100.0,) * 4 for i in range(12 * 24)}
 361      f, t = {}, D - 10 * DAY
 362      while t <= D:
 363          iv = 8 if t < D - 5 * DAY else 4
 364          f[t] = (0.0001, float(iv))
 365          t += iv * H
 366      m = {a: fd.prepare(bars, f) for a in fd.ASSETS}
 367      a = fd.data_audit(m)["BTCUSDT"]
 368      assert len(a["interval_transitions"]) == 1
 369      tr = a["interval_transitions"][0]
 370      assert (tr["from_h"], tr["to_h"], tr["spacing_h"]) == (8.0, 4.0, 8.0)
 371      assert a["spacing_mismatch_semantics_A"] == 0 and a["spacing_mismatch_semantics_B"] == 1
 372  
 373  
 374  def test_K3_audit_only_mode_writes_audit_without_performance(tmp_path, monkeypatch):
 375      m = make_market(rates=ranked_rates)
 376      monkeypatch.setattr(fd, "load", lambda cache: (m, [], [], []))
 377      fd.main(["--outdir", str(tmp_path), "--audit-only"])
 378      assert (tmp_path / "data_audit.json").exists()
 379      assert not (tmp_path / "results.json").exists() and not (tmp_path / "trades.csv").exists()
````

## D1. research/spot_led/PROTOCOL.md (`0a8373b`)
````markdown
# Spot-led price discovery (spot → perp, 5m) BTC/ETH/XRP — předem registrovaný protokol (2026-11-06)

Hypotéza `H-20261106-3` z `automation/IDEAS.md` (externí podnět vlastníka). Výhradně PAPER výzkum podle
`automation/RESEARCH_FRAMEWORK.md` v2. Zapsáno a commitnuto **před** prvním kódem, stažením dat i výsledkem.
Po prvním spuštění se pravidla, dělení ani kritéria nemění; povoleny jsou jen dodatky k načítání dat
zapsané před zobrazením jakékoli metriky.

## Odlišnost od otestovaného (částečný překryv — proto nízká priorita fronty)
- `flow_pressure` (zamítnuto, XRP 15m, PF 0,82): taker-buy podíl na spotu + objem + VWAP, obchod **spot** long.
  Zde: taker-buy podíl jen jako filtr; jádro je **nesoulad** spot vs perp téhož aktiva, obchod na **perpu**, obě strany.
- `btc_lead_lag` (zamítnuto, 1h): BTC vede XRP (mezi aktivy). Zde: spot vede perp **téhož** aktiva, 5m.
- `large_trade_followthrough`, `cross_exchange_residual`, `premium_recovery`: jiné pozorovatelné veličiny
  (velikost obchodu, rozdíl burz, hodinová prémie po extrému).

## Data (veřejná, bez klíčů; stahuje GitHub Actions — síť session je pro Binance blokovaná)
- Binance Vision spot 5m `data/spot/monthly/klines/<S>/5m/<S>-5m-YYYY-MM.zip` (sloupec 5 = objem báze,
  sloupec 9 = taker buy base volume) a USDT-M perp 5m `data/futures/um/monthly/klines/<S>/5m/<S>-5m-YYYY-MM.zip`,
  funding `data/futures/um/monthly/fundingRate/<S>/...`, BTCUSDT, ETHUSDT, XRPUSDT, 2020-01 … 2026-10.
- SHA-256 každého archivu do `data_source.json`. Svíčky se párují **jen přes shodný open time (UTC ms)**; µs časy
  (spot od 2025) se převedou na ms. Nic se nedoplňuje. Audit mezer: počet chybějících 5m časů na trh a měsíc a
  počet časů jen v jednom trhu do `results.json`. Chybějící archiv uvnitř období ⇒ chyba běhu (zastavit, dodatek).

## Pravidla (na každé aktivum zvlášť, společná equity 10 000 USDT)
- Signál po uzavření 5m svíčky s open time T (closes T+5m). Vyžaduje svíčky T a T−5m v obou trzích, objem spotu > 0.
  - podíl = taker_buy_base(T) / volume(T) na spotu;
  - r_spot = close_spot(T) / close_spot(T−5m) − 1; r_perp = close_perp(T) / close_perp(T−5m) − 1.
  - **LONG**: podíl > p_hi a r_spot > +0,20 % a r_perp < +0,10 %.
  - **SHORT**: podíl < p_lo a r_spot < −0,20 % a r_perp > −0,10 %.
- Vstup: perp **open svíčky T+5m** (nejbližší následující; chybí-li tato svíčka v perpu ⇒ signál zahodit).
- Výstup: perp open svíčky T+5m+držení. Chybí-li ⇒ první dostupný perp open po tomto čase, příznak `data_gap=1`.
- Max. 1 pozice na aktivum; signál během otevřené pozice se ignoruje (nový signál smí mít T+5m ≥ čas výstupu).
  Souběžně max. 3 pozice (1 na aktivum).
- Velikost: notional = 10 % realizované equity při vstupu, bez páky. Bez stop-lossu.
- Funding: událost s časem t, kde vstup < t < výstup ⇒ cash flow = −strana × sazba × qty × perp open svíčky v t.

## Náklady
Poplatek 0,095 % + skluz 0,02 % na stranu (round-trip 0,23 % při ×1), náklady ×1 / ×2 / ×3.

## Mřížka a výběr (4 varianty, N +4)
(p_hi, p_lo) ∈ {(0,65; 0,35), (0,70; 0,30)} × držení ∈ {15, 30} min. Výběr jedné varianty na **ladění ×1 podle čistého
zisku**; beze změny do validace a závěrečného testu. Sousedé = 2 varianty lišící se v jednom rozměru.

## Dělení
- Ladění 2020-02-01 … 2022-12-31; validace 2023-01-01 … 2024-12-31; závěrečný test 2025-01-01 … 2026-10-31
  (podle rámce v2 jen „druhá validace“). Obchod patří do období podle času vstupu; výstup nesmí přesáhnout konec období
  (jinak se signál nebere). Každé období začíná na 10 000 USDT.
- Walk-forward: kalendářní roky 2021, 2022, 2023, 2024 se zvolenou variantou, náklady ×2.

## Měřítko
B&H koše 3 perpů stejnými vahami bez rebalance (nákup za první open období, prodej za poslední close, stejné náklady).

## Metriky
Denní equity = realizovaná hotovost na konci dne UTC (pozice trvají ≤ 30 min). Sharpe = průměr/sd denních výnosů ×√365.
Max DD z denní equity. „Obchod“ = vstup–výstup, net_pnl včetně fundingu a nákladů. Informačně: počet obchodů/rok na aktivum,
průměrný hrubý výnos obchodu v bp (aby šlo porovnat s round-trip náklady 23 bp).

## Kritéria (rámec v2, beze změny)
- Stopa A: A1 validace ×1 Sharpe > B&H a max DD < B&H; A2 ≥ 30 obchodů ve validaci; A3 validace ×2 PF > 1,2 a zisk > 0;
  A4 validace ×1 zisk bez 3 nejlepších > 0; A5 závěrečný ×2 zisk > 0, Sharpe > B&H a DD < B&H.
- Stopa B: B1 validace ×2 zisk > 0 a PF > 1,2; B2 max DD ≤ 0,6 × B&H ve validaci i závěrečném testu (×1);
  B3 závěrečný ×2 zisk > 0; B4 validace ×1 bez 3 nejlepších > 0; B5 validace + závěrečný ≥ 20 obchodů; B6 ladění ×1 zisk > 0.
- Při „prošlo“ (A nebo B) navíc: DSR ≥ 0,95 na denních výnosech validace ×1, N = 159 (průběžných 151 + 4 H-20261106-2 + 4 tato),
  V[SR] = 0,5 p.a.; oba sousedé zisk ×2 ve validaci > 0; walk-forward zisk ×2 ve ≥ 3 ze 4 let.
- Prošlo vše ⇒ jen **forward PAPER ve výzkumu ≥ 60 dní**, nikdy „zisková strategie“ ani zásah do produkčních botů.

## Kontrola look-ahead (testy kódu před daty)
Signál ze svíčky T používá jen data s open time ≤ T; vstup až na open T+5m; prefix invariance (připojení budoucích dat
nezmění dřívější obchody); svíčka jen v jednom trhu se nepoužije; funding na hranách se nezapočte; náklady ×1/×2/×3.

## Hlavní rizika
Zdánlivý lead-lag z nesynchronních close (poslední obchod v 5m okně), exekuce za open další svíčky už po vyrovnání cen,
round-trip náklady 0,23 % (×1) proti krátkodobému pohybu.

## Výstupy
`trades.csv`, `results.json`, `RESULTS.md`, `data_source.json`; řádek v `automation/STRATEGY_REGISTRY.md`; draft PR do
`research/autopilot`. Spuštění: commit UTC času do `research/spot_led/RUN_REQUEST` (nejdřív 2026-11-07 UTC, denní limit).

## Dodatek 0 (2026-11-06, před kódem i před stažením jakýchkoli dat)
- Cena pro funding: perp open svíčky v čase události; chybí-li, close poslední dřívější perp svíčky.
- Equity pro velikost pozice = počáteční kapitál + net P/L obchodů uzavřených nejpozději v čase vstupu.
- Výběr varianty při shodě zisku = první v pořadí mřížky. `trades.csv` nad 50 MB se uloží jako `trades.csv.gz`.
Pravidla, dělení ani kritéria se nemění.

## Dodatek 1 (2026-11-06 ~16:55 UTC, po oponentuře ChatGPT kolo 2; před stažením dat — žádný tržní výsledek dosud neexistuje)
Opravy a upřesnění implementace (signál, mřížka, dělení ani kritéria se nemění):
- **Denní equity** zahrnuje pozice otevřené přes půlnoc: close poslední svíčky dne, vstupní náklady, funding do půlnoci.
- **Výstup při mezeře** nejvýš o 60 min později (první dostupný perp open ≤ plán + 60 min, `data_gap = 1`); jinak
  `data_gap = 2` = poslední pozorovaný close před plánem, čas plán + 60 min — označeno jako **nerealizovatelné**.
- **Konec období** posuzován jen časem: plánovaný výstup + 60 min < konec období (žádný pohled na existenci budoucích dat).
- Souběžné vstupy na více aktivech se dimenzují ze stejné realizované equity ⇒ nezávisí na pořadí symbolů (test).
- **B&H 3 perpů účtuje skutečný funding** (long platí kladnou sazbu) — stejná chyba jako R2 v PR #29.
- **Nedefinované DSR** (nulový rozptyl) = `null` + důvod, brána neprošla; scénáře DSR N ∈ {159, 318, 636} × V[SR] ∈ {0,5; 1; 2}.
- **Citlivost na latenci** (předem, bez výběru): zvolená varianta se vstupem o 1 svíčku později (open T+10 min),
  validace a závěrečný test ×1/×2, jen informativně. Je-li výsledek „prošlo“, ale latence +5 min dává ve validaci ×2
  ztrátu, nebo existují výstupy `data_gap = 2` ⇒ verdikt „NEROZHODNUTO“ do ruční revize.
- „Walk-forward“ 2021–24 = roční stabilita fixní varianty (pro 2021–22 ne čistý OOS).

## Dodatek 2 (2026-11-06 ~17:15 UTC, po oponentuře ChatGPT kolo 3; stále před stažením dat)
- **Jednotná konvence dne** pro strategii i benchmark: den d = [d 00:00, d+1 00:00). Ocenění na konci dne proběhne
  **před** událostmi v přesně 00:00 — funding, výstup i vstup v 00:00 patří novému dni; pozice otevřená v okamžiku
  konce dne (vstup < konec ≤ výstup) se ocení close poslední uzavřené svíčky dne a fundingem t < konec.
- **Nikdy budoucí cena:** `day_close`, `close_before` i `perp_price_at` berou jen svíčky uzavřené do daného času;
  prázdný prefix ⇒ None. Benchmark kupuje aktivum za open první svíčky v [začátek, začátek + 60 min], jinak je aktivum
  po celé období hotovost (`unavailable_at_start`).
- **Náhradní ceny s auditem:** každá náhrada má účel, stáří a označení obchodu (`funding_price_fallbacks`, max. stáří,
  `stale_mtm`); stáří > 60 min ⇒ obchod `unevaluable`. Totéž u benchmarku (`stale_valuations`, `funding_price_fallbacks`).
- **Úplnost fundingu:** `parse_funding` drží `funding_interval_hours`; každý obchod má `funding_gaps` (chybějící očekávaná
  událost ve držení se neodhaduje jako nula, jen se označí). Sémantika pole stejná jako v PR #29 (A) — o ní rozhodne
  datový audit PR #29 (`data_audit.json`) před během výkonnosti; R9 se spustí až po tomto rozhodnutí.
- Cokoli z výše uvedeného nenulové + „prošlo“ ⇒ verdikt „NEROZHODNUTO“.
````

## D2. research/spot_led/run.py (`0a8373b`)
````python
   1  """Spot-led price discovery spot → USDT-M perp, 5m, BTC/ETH/XRP (H-20261106-3) — backtest podle PROTOCOL.md.
   2  PAPER výzkum, veřejná data Binance Vision, bez klíčů a objednávek.
   3  
   4      python -m research.spot_led.run --cache /tmp/vision-5m --outdir research/spot_led
   5  """
   6  import argparse
   7  import bisect
   8  import csv
   9  import hashlib
  10  import heapq
  11  import io
  12  import json
  13  import math
  14  import sys
  15  import urllib.error
  16  import urllib.request
  17  import zipfile
  18  from datetime import date, datetime, timedelta, timezone
  19  from pathlib import Path
  20  
  21  ASSETS = ("BTCUSDT", "ETHUSDT", "XRPUSDT")
  22  FIRST_MONTH = (2020, 1)
  23  LAST_MONTH = (2026, 10)
  24  FEE, SLIP = 0.00095, 0.0002
  25  COST_MULTIPLIERS = (1, 2, 3)
  26  GRID = [(th, hold) for th in (0.65, 0.70) for hold in (15, 30)]  # (p_hi; p_lo = 1 − p_hi, držení min)
  27  R_SPOT, R_PERP = 0.002, 0.001
  28  PERIODS = {"tuning": ("2020-02-01", "2022-12-31"),
  29             "validation": ("2023-01-01", "2024-12-31"),
  30             "final_test": ("2025-01-01", "2026-10-31")}
  31  WF_YEARS = (2021, 2022, 2023, 2024)
  32  START_EQUITY = 10_000.0
  33  FRACTION = 0.10
  34  DSR_N, DSR_VAR_ANNUAL = 159, 0.5
  35  BAR = 300_000
  36  HOUR_MS = 3_600_000
  37  DAY_MS = 86_400_000
  38  
  39  
  40  def vt(th, hold):
  41      return f"P{int(round(th * 100))}_H{hold}"
  42  
  43  
  44  # ------------------------------------------------------------------ data
  45  def months():
  46      y, m = FIRST_MONTH
  47      while (y, m) <= LAST_MONTH:
  48          yield y, m
  49          y, m = (y + 1, 1) if m == 12 else (y, m + 1)
  50  
  51  
  52  def fetch(url):
  53      req = urllib.request.Request(url, headers={"User-Agent": "paper-research/1.0"})
  54      with urllib.request.urlopen(req, timeout=120) as r:
  55          return r.read()
  56  
  57  
  58  def _csv_rows(payload):
  59      with zipfile.ZipFile(io.BytesIO(payload)) as z:
  60          text = z.read(z.namelist()[0]).decode()
  61      return [r for r in csv.reader(io.StringIO(text)) if r and r[0].strip().isdigit()]
  62  
  63  
  64  def _ms(ts):
  65      return ts // 1000 if ts > 10 ** 14 else ts
  66  
  67  
  68  def parse_spot(payload):
  69      """→ [(ts, close, volume, taker_buy_base)]"""
  70      return [(_ms(int(r[0])), float(r[4]), float(r[5]), float(r[9])) for r in _csv_rows(payload)]
  71  
  72  
  73  def parse_perp(payload):
  74      """→ [(ts, open, close)]"""
  75      return [(_ms(int(r[0])), float(r[1]), float(r[4])) for r in _csv_rows(payload)]
  76  
  77  
  78  def normalize_funding_ts(ts):
  79      near = round(ts / HOUR_MS) * HOUR_MS
  80      if abs(ts - near) > 1000:
  81          raise ValueError(f"funding timestamp {ts} je {ts - near} ms od celé hodiny")
  82      return near
  83  
  84  
  85  def parse_funding(payload):
  86      """→ [(normalizovaný čas, sazba, funding_interval_hours)] (dodatek 2: interval kvůli kontrole úplnosti)."""
  87      return [(normalize_funding_ts(_ms(int(r[0]))), float(r[2]), float(r[1])) for r in _csv_rows(payload)]
  88  
  89  
  90  def urls(asset):
  91      b = "https://data.binance.vision/data"
  92      for y, m in months():
  93          tag = f"{y}-{m:02d}"
  94          yield "spot", (y, m), f"{b}/spot/monthly/klines/{asset}/5m/{asset}-5m-{tag}.zip"
  95          yield "perp", (y, m), f"{b}/futures/um/monthly/klines/{asset}/5m/{asset}-5m-{tag}.zip"
  96          yield "fr", (y, m), f"{b}/futures/um/monthly/fundingRate/{asset}/{asset}-fundingRate-{tag}.zip"
  97  
  98  
  99  def load(cache, fetcher=fetch):
 100      market, manifest, missing, fatal = {}, [], [], []
 101      parsers = {"spot": parse_spot, "perp": parse_perp, "fr": parse_funding}
 102      for a in ASSETS:
 103          raw = {"spot": {}, "perp": {}, "fr": {}}
 104          present, miss = {k: [] for k in raw}, {k: [] for k in raw}
 105          for kind, ym, url in urls(a):
 106              p = Path(cache) / kind / url.rsplit("/", 1)[1]
 107              if not p.exists():
 108                  try:
 109                      payload = fetcher(url)
 110                  except urllib.error.HTTPError as e:
 111                      missing.append({"url": url, "http": e.code})
 112                      miss[kind].append(ym)
 113                      continue
 114                  p.parent.mkdir(parents=True, exist_ok=True)
 115                  p.write_bytes(payload)
 116              payload = p.read_bytes()
 117              present[kind].append(ym)
 118              rows = parsers[kind](payload)
 119              for r in rows:
 120                  raw[kind][r[0]] = r[1:] if kind != "fr" else (r[1], r[2])
 121              manifest.append({"url": url, "sha256": hashlib.sha256(payload).hexdigest(), "rows": len(rows)})
 122          for kind in raw:
 123              if present[kind]:
 124                  first = min(present[kind])
 125                  fatal += [{"asset": a, "kind": kind, "month": f"{y}-{m:02d}"} for (y, m) in miss[kind] if (y, m) > first]
 126              else:
 127                  fatal.append({"asset": a, "kind": kind, "month": "all"})
 128          market[a] = prepare(raw["spot"], raw["perp"], raw["fr"])
 129      return market, manifest, missing, fatal
 130  
 131  
 132  def prepare(spot, perp, fund):
 133      """spot {ts: (close, vol, taker_buy)}, perp {ts: (open, close)}, fund {ts: rate | (rate, interval_h)}.
 134      Holá sazba (syntetické testy) = interval 8 h."""
 135      perp_ts = sorted(perp)
 136      f = {ts: (v if isinstance(v, tuple) else (v, 8.0)) for ts, v in sorted(fund.items())}
 137      return {"spot": spot, "perp": perp, "perp_ts": perp_ts, "funding": {ts: v[0] for ts, v in f.items()},
 138              "finterval": {ts: v[1] for ts, v in f.items()}, "fts": list(f), "features": features(spot, perp)}
 139  
 140  
 141  def features(spot, perp):
 142      """Pro každý spot čas T se svíčkami T a T−5m v obou trzích: (T, podíl, r_spot, r_perp). Jen data ≤ T."""
 143      out = []
 144      for T in sorted(spot):
 145          s, sp = spot[T], spot.get(T - BAR)
 146          p, pp = perp.get(T), perp.get(T - BAR)
 147          if sp is None or p is None or pp is None or s[1] <= 0 or sp[0] <= 0 or pp[1] <= 0:
 148              continue
 149          out.append((T, s[2] / s[1], s[0] / sp[0] - 1, p[1] / pp[1] - 1))
 150      return out
 151  
 152  
 153  def gap_audit(m):
 154      spot, perp = m["spot"], m["perp"]
 155      def missing(ts_sorted):
 156          return sum(max(0, (b - a) // BAR - 1) for a, b in zip(ts_sorted, ts_sorted[1:]))
 157      ss = set(spot)
 158      ps = set(perp)
 159      return {"spot_bars": len(spot), "perp_bars": len(perp), "spot_missing_5m": missing(sorted(spot)),
 160              "perp_missing_5m": missing(m["perp_ts"]), "spot_only": len(ss - ps), "perp_only": len(ps - ss),
 161              "usable_signal_bars": len(m["features"])}
 162  
 163  
 164  # ------------------------------------------------------------------ simulace
 165  def ms_of(d):
 166      return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)
 167  
 168  
 169  def date_of(ms):
 170      return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date()
 171  
 172  
 173  MAX_PRICE_AGE_MS = 60 * 60_000  # dodatek 2: náhradní cena starší než 60 min ⇒ obchod/den nehodnotitelný
 174  
 175  
 176  def perp_price_at(m, t):
 177      """(cena, stáří ms, náhrada?): open svíčky v t (stáří 0, bez náhrady); chybí-li, close poslední svíčky UZAVŘENÉ
 178      do t (stáří = t − čas uzavření, náhrada = True). Žádná dřívější svíčka ⇒ None — nikdy budoucí cena (dodatek 2)."""
 179      b = m["perp"].get(t)
 180      if b is not None:
 181          return b[0], 0, False
 182      i = bisect.bisect_right(m["perp_ts"], t - BAR) - 1
 183      if i < 0:
 184          return None
 185      ts = m["perp_ts"][i]
 186      return m["perp"][ts][1], t - (ts + BAR), True
 187  
 188  
 189  def funding_chain_gaps(m, lo, hi):
 190      """Úplnost funding řady pro (lo, hi]: chybí předchozí událost ≤ lo (None), rozestup ≠ interval dřívější události,
 191      nebo chybí očekávaná událost ≤ hi. Chybějící událost se nikdy nepočítá jako nulová sazba — jen se označí."""
 192      fts = m["fts"]
 193      i = bisect.bisect_right(fts, lo) - 1
 194      if i < 0:
 195          return None
 196      gaps, k = 0, i
 197      while k + 1 < len(fts) and fts[k + 1] <= hi:
 198          if fts[k + 1] - fts[k] != m["finterval"][fts[k]] * HOUR_MS:
 199              gaps += 1
 200          k += 1
 201      if fts[k] + m["finterval"][fts[k]] * HOUR_MS <= hi:
 202          gaps += 1
 203      return gaps
 204  
 205  
 206  MAX_EXIT_DELAY_MS = 60 * 60_000  # dodatek 1: výstup se smí kvůli mezeře zpozdit nejvýš o 60 min
 207  
 208  
 209  def candidates(m, asset, start_ms, end_ms, th, hold, delay_bars=0):
 210      """Kandidátní obchody jednoho aktiva (nezávislé na equity): bez překryvu, výstup uvnitř období.
 211      delay_bars: informativní citlivost na latenci (vstup o N svíček později), výběr varianty neovlivňuje.
 212      Okraj období se posuzuje jen podle času (plánovaný výstup + max. zpoždění < konec), ne podle existence dat."""
 213      hold_ms = hold * 60_000
 214      out, free_from = [], -1
 215      feats = m["features"]
 216      i = bisect.bisect_left(feats, (start_ms - BAR,))  # vstup (T+5m) ≥ start
 217      for T, share, rs, rp in feats[i:]:
 218          entry_t = T + BAR * (1 + delay_bars)
 219          if entry_t >= end_ms:
 220              break
 221          if entry_t < start_ms or T + BAR < free_from:
 222              continue
 223          if share > th and rs > R_SPOT and rp < R_PERP:
 224              side = 1
 225          elif share < 1 - th and rs < -R_SPOT and rp > -R_PERP:
 226              side = -1
 227          else:
 228              continue
 229          planned = entry_t + hold_ms
 230          if planned + MAX_EXIT_DELAY_MS >= end_ms:
 231              continue
 232          if entry_t not in m["perp"]:
 233              continue
 234          j = bisect.bisect_left(m["perp_ts"], planned)
 235          if j < len(m["perp_ts"]) and m["perp_ts"][j] <= planned + MAX_EXIT_DELAY_MS:
 236              exit_t = m["perp_ts"][j]
 237              exit_px = m["perp"][exit_t][0]
 238              gap = int(exit_t != planned)
 239          else:  # mezera delší než limit ⇒ DATA_GAP: poslední pozorovaný close před plánovaným výstupem (nerealizovatelné)
 240              k = bisect.bisect_left(m["perp_ts"], planned) - 1
 241              exit_t = planned + MAX_EXIT_DELAY_MS
 242              exit_px = m["perp"][m["perp_ts"][k]][1]
 243              gap = 2
 244          # funding: události s entry_t < t < exit_t (seznam pro denní ocenění přes půlnoc)
 245          f_events, f_fallbacks, f_max_age, unevaluable = [], 0, 0, 0
 246          t = (entry_t // HOUR_MS + 1) * HOUR_MS
 247          while t < exit_t:
 248              if t in m["funding"]:
 249                  pa = perp_price_at(m, t)
 250                  if pa is None or pa[1] > MAX_PRICE_AGE_MS:
 251                      unevaluable = 1
 252                  if pa is not None:
 253                      f_fallbacks += pa[2]
 254                      f_max_age = max(f_max_age, pa[1])
 255                      f_events.append((t, -side * m["funding"][t] * pa[0]))
 256              t += HOUR_MS
 257          fg = funding_chain_gaps(m, entry_t, exit_t - 1)
 258          out.append({"asset": asset, "side": side, "signal_ts": T, "entry_ts": entry_t, "exit_ts": exit_t,
 259                      "entry": m["perp"][entry_t][0], "exit": exit_px, "funding_unit": sum(x for _, x in f_events),
 260                      "funding_events": f_events, "share": share, "r_spot": rs, "r_perp": rp, "data_gap": gap,
 261                      "funding_price_fallbacks": f_fallbacks, "funding_price_max_age_min": f_max_age / 60_000,
 262                      "funding_gaps": 1 if fg is None else fg, "unevaluable": unevaluable})
 263          free_from = exit_t
 264      return out
 265  
 266  
 267  def close_before(m, t):
 268      """(close, stáří ms) poslední perp svíčky uzavřené nejpozději v t; žádná ⇒ None (nikdy budoucí cena)."""
 269      i = bisect.bisect_right(m["perp_ts"], t - BAR) - 1
 270      if i < 0:
 271          return None
 272      ts = m["perp_ts"][i]
 273      return m["perp"][ts][1], t - (ts + BAR)
 274  
 275  
 276  def simulate(market, start, end, th, hold, mult, variant="", delay_bars=0):
 277      """Sdílená equity: notional = 10 % realizované equity při vstupu. Vrací (obchody, denní equity).
 278      Denní equity = realizované obchody + ocenění pozic otevřených přes půlnoc (close poslední svíčky dne,
 279      vstupní náklady, funding do půlnoci) — oprava podle oponentury (bod G)."""
 280      c = (FEE + SLIP) * mult
 281      s_ms, e_ms = ms_of(start), ms_of(end) + DAY_MS
 282      cands = sorted((x for a in ASSETS for x in candidates(market[a], a, s_ms, e_ms, th, hold, delay_bars)),
 283                     key=lambda x: (x["entry_ts"], x["asset"]))
 284      cash, pending, trades = START_EQUITY, [], []
 285      for x in cands:
 286          while pending and pending[0][0] <= x["entry_ts"]:
 287              _, _, tr = heapq.heappop(pending)
 288              cash += tr["net_pnl"]
 289          notional = FRACTION * cash
 290          qty = notional / x["entry"]
 291          gross = x["side"] * qty * (x["exit"] - x["entry"])
 292          costs = notional * c + qty * x["exit"] * c
 293          fund = qty * x["funding_unit"]
 294          tr = {**x, "variant": variant, "cost_mult": mult, "qty": qty, "notional": notional, "gross": gross,
 295                "funding": fund, "costs": costs, "net_pnl": gross + fund - costs, "cost_in": notional * c,
 296                "gross_bp": x["side"] * (x["exit"] / x["entry"] - 1) * 1e4}
 297          trades.append(tr)
 298          heapq.heappush(pending, (x["exit_ts"], len(trades), tr))
 299      # Jednotná konvence dne (dodatek 2, stejná pro benchmark): den d = [d 00:00, d+1 00:00); ocenění na konci dne
 300      # proběhne PŘED událostmi v přesně 00:00 (funding, výstup, vstup v 00:00 patří novému dni). Pozice otevřená v
 301      # okamžiku konce dne (vstup < konec ≤ výstup) se ocení close poslední uzavřené svíčky dne.
 302      realized_by_day, overnight = {}, {}
 303      for tr in trades:
 304          d = date_of(tr["exit_ts"])
 305          realized_by_day[d] = realized_by_day.get(d, 0.0) + tr["net_pnl"]
 306          tr["stale_mtm"] = 0
 307          day_end = (tr["entry_ts"] // DAY_MS + 1) * DAY_MS
 308          while day_end <= tr["exit_ts"]:
 309              p, age = close_before(market[tr["asset"]], day_end)
 310              tr["stale_mtm"] += age > MAX_PRICE_AGE_MS
 311              mtm = tr["side"] * tr["qty"] * (p - tr["entry"]) - tr["cost_in"] + \
 312                  tr["qty"] * sum(v for t, v in tr["funding_events"] if t < day_end)
 313              dd = date_of(day_end - 1)
 314              overnight[dd] = overnight.get(dd, 0.0) + mtm
 315              day_end += DAY_MS
 316      curve, eq, d = {}, START_EQUITY, start
 317      while d <= end:
 318          eq += realized_by_day.get(d, 0.0)
 319          curve[d] = eq + overnight.get(d, 0.0)
 320          d += timedelta(days=1)
 321      return trades, curve
 322  
 323  
 324  # ------------------------------------------------------------------ metriky
 325  def curve_metrics(curve, start_value):
 326      vals = [curve[d] for d in sorted(curve)]
 327      rets = [vals[0] / start_value - 1] + [vals[k] / vals[k - 1] - 1 for k in range(1, len(vals))]
 328      mu = sum(rets) / len(rets)
 329      sd = math.sqrt(sum((r - mu) ** 2 for r in rets) / (len(rets) - 1)) if len(rets) > 1 else 0.0
 330      peak, mdd = start_value, 0.0
 331      for v in vals:
 332          peak = max(peak, v)
 333          mdd = max(mdd, 1 - v / peak)
 334      return {"return_pct": round((vals[-1] / start_value - 1) * 100, 4),
 335              "sharpe": round(mu / sd * math.sqrt(365), 4) if sd > 0 else 0.0,
 336              "max_drawdown_pct": round(mdd * 100, 4)}, rets
 337  
 338  
 339  def trade_metrics(trades, start, end):
 340      pnl = [t["net_pnl"] for t in trades]
 341      gains = sum(p for p in pnl if p > 0)
 342      losses = -sum(p for p in pnl if p < 0)
 343      top3 = sum(sorted(pnl, reverse=True)[:3])
 344      years = max((end - start).days + 1, 1) / 365.25
 345      return {"trades": len(pnl), "net_pnl": round(sum(pnl), 4),
 346              "profit_factor": round(gains / losses, 4) if losses > 0 else (None if gains == 0 else 999.0),
 347              "net_without_top3": round(sum(pnl) - top3, 4),
 348              "funding": round(sum(t["funding"] for t in trades), 4),
 349              "costs": round(sum(t["costs"] for t in trades), 4),
 350              "long_trades": sum(1 for t in trades if t["side"] == 1),
 351              "short_trades": sum(1 for t in trades if t["side"] == -1),
 352              "data_gap_exits": sum(1 for t in trades if t["data_gap"]),
 353              "data_gap_unrealizable_exits": sum(1 for t in trades if t["data_gap"] == 2),
 354              "funding_price_fallback_trades": sum(1 for t in trades if t["funding_price_fallbacks"]),
 355              "funding_price_max_age_min": max([t["funding_price_max_age_min"] for t in trades], default=0),
 356              "funding_gap_trades": sum(1 for t in trades if t["funding_gaps"]),
 357              "unevaluable_trades": sum(t["unevaluable"] for t in trades),
 358              "stale_mtm_trades": sum(1 for t in trades if t.get("stale_mtm")),
 359              "avg_gross_bp": round(sum(t["gross_bp"] for t in trades) / len(trades), 3) if trades else None,
 360              "trades_per_year_per_asset": {a: round(sum(1 for t in trades if t["asset"] == a) / years, 1)
 361                                            for a in ASSETS}}
 362  
 363  
 364  def run(market, start, end, mult, th, hold, variant, delay_bars=0):
 365      trades, curve = simulate(market, start, end, th, hold, mult, variant, delay_bars)
 366      cm, rets = curve_metrics(curve, START_EQUITY)
 367      return {**cm, **trade_metrics(trades, start, end)}, trades, rets
 368  
 369  
 370  def day_close(m, d):
 371      """(close, stáří ms) poslední svíčky uzavřené do konce dne d; prázdný prefix ⇒ None (oprava: dřív index −1 = budoucí cena)."""
 372      return close_before(m, ms_of(d) + DAY_MS)
 373  
 374  
 375  def buy_hold(market, start, end, mult):
 376      """B&H 3 perpů stejnými vahami, 1× bez páky, včetně skutečného fundingu (long platí kladnou sazbu).
 377      Konvence dne jako u strategie: událost v přesně 00:00 patří novému dni. Nákup za open první svíčky v [start, start + 60 min];
 378      aktivum bez svíčky v tomto okně = hotovost po celé období (`unavailable_at_start`), nikdy pozdější/budoucí cena."""
 379      c = (FEE + SLIP) * mult
 380      t0 = ms_of(start)
 381      t_end = ms_of(end) + DAY_MS
 382      share = START_EQUITY / len(ASSETS)
 383      qty, cash, unavailable = {}, 0.0, []
 384      for a in ASSETS:
 385          m = market[a]
 386          j = bisect.bisect_left(m["perp_ts"], t0)
 387          if j < len(m["perp_ts"]) and m["perp_ts"][j] <= t0 + MAX_PRICE_AGE_MS:
 388              qty[a] = share * (1 - c) / m["perp"][m["perp_ts"][j]][0]
 389          else:
 390              cash += share
 391              unavailable.append(a)
 392      events = sorted((t, a) for a in qty for t in market[a]["funding"] if t0 < t < t_end)
 393      k, funding, curve, d, stale, fb = 0, 0.0, {}, start, 0, 0
 394      while d <= end:
 395          t_day = ms_of(d) + DAY_MS
 396          while k < len(events) and events[k][0] < t_day:
 397              te, a = events[k]
 398              pa = perp_price_at(market[a], te)
 399              fb += pa[2]
 400              stale += pa[1] > MAX_PRICE_AGE_MS
 401              funding -= market[a]["funding"][te] * qty[a] * pa[0]
 402              k += 1
 403          val = 0.0
 404          for a, q in qty.items():
 405              p, age = day_close(market[a], d)
 406              stale += age > MAX_PRICE_AGE_MS
 407              val += q * p
 408          curve[d] = cash + funding + val
 409          d += timedelta(days=1)
 410      curve[end] = cash + funding + (curve[end] - cash - funding) * (1 - c)
 411      cm, _ = curve_metrics(curve, START_EQUITY)
 412      return {**cm, "net_pnl": round(curve[end] - START_EQUITY, 4), "funding": round(funding, 4),
 413              "unavailable_at_start": unavailable, "stale_valuations": stale, "funding_price_fallbacks": fb}
 414  
 415  
 416  def safe_dsr(rets, n, var_annual):
 417      """Nedefinované DSR (nulový rozptyl, např. 0 obchodů) = None + důvod; brána pak neprošla."""
 418      sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
 419      from tools.research.deflated_sharpe import dsr_from_returns
 420      try:
 421          return {**dsr_from_returns(rets, n, var_annual / 365), "undefined_reason": None}
 422      except (ValueError, ZeroDivisionError) as e:
 423          return {"dsr": None, "undefined_reason": str(e), "n_trials": n, "var_trials": var_annual / 365}
 424  
 425  
 426  def evaluate(res, bh):
 427      v1, v2 = res["validation"]["x1"], res["validation"]["x2"]
 428      f2, t1 = res["final_test"]["x2"], res["tuning"]["x1"]
 429      bv, bf = bh["validation"]["x1"], bh["final_test"]["x2"]
 430      a = {"A1_sharpe_dd": v1["sharpe"] > bv["sharpe"] and v1["max_drawdown_pct"] < bv["max_drawdown_pct"],
 431           "A2_trades_ge_30": v1["trades"] >= 30,
 432           "A3_x2_pf_profit": (v2["profit_factor"] or 0) > 1.2 and v2["net_pnl"] > 0,
 433           "A4_wo_top3": v1["net_without_top3"] > 0,
 434           "A5_final_x2": f2["net_pnl"] > 0 and f2["sharpe"] > bf["sharpe"]
 435           and f2["max_drawdown_pct"] < bf["max_drawdown_pct"]}
 436      b = {"B1_val_x2_profit_pf": v2["net_pnl"] > 0 and (v2["profit_factor"] or 0) > 1.2,
 437           "B2_dd_le_0_6_bh": v1["max_drawdown_pct"] <= 0.6 * bv["max_drawdown_pct"]
 438           and res["final_test"]["x1"]["max_drawdown_pct"] <= 0.6 * bh["final_test"]["x1"]["max_drawdown_pct"],
 439           "B3_final_x2_profit": f2["net_pnl"] > 0,
 440           "B4_val_wo_top3": v1["net_without_top3"] > 0,
 441           "B5_trades_ge_20": v1["trades"] + res["final_test"]["x1"]["trades"] >= 20,
 442           "B6_tuning_x1_profit": t1["net_pnl"] > 0}
 443      return a, b
 444  
 445  
 446  def neighbors(th, hold):
 447      return [(t2, h2) for (t2, h2) in GRID if (t2 == th) != (h2 == hold)]
 448  
 449  
 450  def pdate(s):
 451      return date.fromisoformat(s)
 452  
 453  
 454  def iso(ms):
 455      return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()
 456  
 457  
 458  def trade_row(period, t):
 459      return {"period": period, "variant": t["variant"], "cost_mult": t["cost_mult"], "asset": t["asset"],
 460              "side": "LONG" if t["side"] == 1 else "SHORT", "signal_bar_utc": iso(t["signal_ts"]),
 461              "entry_utc": iso(t["entry_ts"]), "exit_utc": iso(t["exit_ts"]), "entry": t["entry"], "exit": t["exit"],
 462              "taker_buy_share": round(t["share"], 6), "r_spot": round(t["r_spot"], 6), "r_perp": round(t["r_perp"], 6),
 463              "qty": round(t["qty"], 10), "notional": round(t["notional"], 6), "gross": round(t["gross"], 6),
 464              "funding": round(t["funding"], 6), "costs": round(t["costs"], 6), "data_gap": t["data_gap"],
 465              "funding_price_fallbacks": t["funding_price_fallbacks"], "funding_gaps": t["funding_gaps"],
 466              "unevaluable": t["unevaluable"], "stale_mtm": t.get("stale_mtm", 0),
 467              "net_pnl": round(t["net_pnl"], 6)}
 468  
 469  
 470  def main(argv=None):
 471      ap = argparse.ArgumentParser()
 472      ap.add_argument("--cache", default="/tmp/vision-5m")
 473      ap.add_argument("--outdir", default="research/spot_led")
 474      args = ap.parse_args(argv)
 475      out = Path(args.outdir)
 476      market, manifest, missing, fatal = load(args.cache)
 477      (out / "data_source.json").write_text(json.dumps({"archives": manifest, "missing": missing}, indent=1))
 478      if fatal:
 479          print("FATAL missing archives after first available month", json.dumps(fatal[:30]))
 480          sys.exit(2)
 481      audit = {a: gap_audit(market[a]) for a in ASSETS}
 482      print("GAP_AUDIT", json.dumps(audit))
 483  
 484      rows, results, tune, rets_store = [], {}, {}, {}
 485      for (th, hold) in GRID:
 486          tag = vt(th, hold)
 487          results[tag] = {}
 488          for p, (s, e) in PERIODS.items():
 489              results[tag][p] = {}
 490              for m in COST_MULTIPLIERS:
 491                  r, trades, rets = run(market, pdate(s), pdate(e), m, th, hold, tag)
 492                  results[tag][p][f"x{m}"] = r
 493                  rets_store[(tag, p, m)] = rets
 494                  rows += [trade_row(p, t) for t in trades]
 495          tune[tag] = results[tag]["tuning"]["x1"]
 496      chosen = max(GRID, key=lambda g: (tune[vt(*g)]["net_pnl"], -GRID.index(g)))
 497      ctag = vt(*chosen)
 498      bh = {p: {f"x{m}": buy_hold(market, pdate(s), pdate(e), m) for m in COST_MULTIPLIERS}
 499            for p, (s, e) in PERIODS.items()}
 500      wf = {}
 501      for y in WF_YEARS:
 502          r, trades, _ = run(market, date(y, 1, 1), date(y, 12, 31), 2, chosen[0], chosen[1], ctag)
 503          wf[str(y)] = r
 504          rows += [trade_row(f"wf_{y}", t) for t in trades]
 505  
 506      res = results[ctag]
 507      track_a, track_b = evaluate(res, bh)
 508      passed_a, passed_b = all(track_a.values()), all(track_b.values())
 509      vrets = rets_store[(ctag, "validation", 1)]
 510      dsr = safe_dsr(vrets, DSR_N, DSR_VAR_ANNUAL)
 511      dsr_sens = {f"N{n}_V{v}": safe_dsr(vrets, n, v)["dsr"] for n in (159, 318, 636) for v in (0.5, 1.0, 2.0)}
 512      latency = {p: {f"x{m}": run(market, pdate(PERIODS[p][0]), pdate(PERIODS[p][1]), m, chosen[0], chosen[1],
 513                                  ctag + "_lat5m", delay_bars=1)[0] for m in (1, 2)} for p in ("validation", "final_test")}
 514      nb = {vt(*g): results[vt(*g)]["validation"]["x2"]["net_pnl"] for g in neighbors(*chosen)}
 515      wf_pos = sum(1 for y in wf.values() if y["net_pnl"] > 0)
 516      robust = {"dsr_ge_0_95": dsr["dsr"] is not None and dsr["dsr"] >= 0.95, "neighbors_val_x2_profit": all(v > 0 for v in nb.values()),
 517                "walk_forward_ge_3_of_4": wf_pos >= 3}
 518      verdict = ("KANDIDÁT NA FORWARD PAPER" if (passed_a or passed_b) and all(robust.values()) else "ZAMÍTNUTO")
 519      gap_flags = sum(res[p]["x1"][k] for p in PERIODS for k in (
 520          "data_gap_unrealizable_exits", "funding_price_fallback_trades", "funding_gap_trades", "unevaluable_trades",
 521          "stale_mtm_trades")) + sum(bh[p]["x1"]["stale_valuations"] + len(bh[p]["x1"]["unavailable_at_start"])
 522                                     for p in PERIODS)
 523      if verdict.startswith("KANDIDÁT") and (gap_flags or latency["validation"]["x2"]["net_pnl"] <= 0):
 524          verdict = "NEROZHODNUTO — problémy dat (mezery, náhradní/zastaralé ceny, neúplný funding) nebo ztráta při latenci +5 min"
 525      payload = {"protocol": "research/spot_led/PROTOCOL.md", "chosen": ctag, "tuning_selection_x1": tune,
 526                 "strategy": results, "buy_hold_equal_3": bh, "walk_forward_x2": wf, "neighbors_val_x2": nb,
 527                 "track_a": track_a, "track_b": track_b, "passed_a": passed_a, "passed_b": passed_b,
 528                 "dsr_validation_x1": dsr,
 529                 "dsr_note": "N = 159 je pracovní odhad (ne doložená horní mez); V[SR] = 0,5 p.a. je předpoklad",
 530                 "dsr_sensitivity_scenarios": dsr_sens, "latency_plus_5m_info": latency,
 531                 "walk_forward_note": "roční stabilita fixní varianty vybrané na 2020-02…2022; pro 2021–22 NE čistý OOS",
 532                 "robustness": robust, "gap_audit": audit, "verdict": verdict}
 533      (out / "results.json").write_text(json.dumps(payload, indent=1, default=str))
 534      with open(out / "trades.csv", "w", newline="") as fh:
 535          w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["period"])
 536          w.writeheader()
 537          w.writerows(rows)
 538      if (out / "trades.csv").stat().st_size > 50 * 2 ** 20:  # limit souborů GitHubu
 539          import gzip
 540          with open(out / "trades.csv", "rb") as src, gzip.open(out / "trades.csv.gz", "wb") as dst:
 541              dst.write(src.read())
 542          (out / "trades.csv").unlink()
 543      print("SUMMARY", json.dumps({"chosen": ctag, "verdict": verdict, "track_a": track_a, "track_b": track_b,
 544                                   "robust": robust, "dsr": dsr["dsr"], "dsr_sens": dsr_sens, "neighbors": nb,
 545                                   "latency_val_x2": latency["validation"]["x2"]["net_pnl"],
 546                                   "val": res["validation"], "final": res["final_test"], "tuning": res["tuning"],
 547                                   "bh_val": bh["validation"]["x1"], "bh_final": bh["final_test"]["x2"],
 548                                   "wf": {k: v["net_pnl"] for k, v in wf.items()}}, default=str))
 549  
 550  
 551  if __name__ == "__main__":
 552      main()
````

## D3. tests/test_spot_led.py (`0a8373b`)
````python
   1  """Mechanika backtestu H-20261106-3 na syntetických datech (není důkaz ziskovosti)."""
   2  from datetime import date
   3  
   4  import pytest
   5  
   6  from research.spot_led import run as sl
   7  
   8  BAR = sl.BAR
   9  H = sl.HOUR_MS
  10  START = date(2021, 1, 1)
  11  T0 = sl.ms_of(START)
  12  
  13  
  14  def flat(n_bars=2000, t0=T0):
  15      spot = {t0 + i * BAR: (100.0, 10.0, 5.0) for i in range(n_bars)}
  16      perp = {t0 + i * BAR: (100.0, 100.0) for i in range(n_bars)}
  17      return spot, perp
  18  
  19  
  20  def market_with(events=None, n_bars=2000, fund=None, drop_perp=()):
  21      """events: {bar_index: (spot_close, taker_share, perp_close)} pro BTC; ostatní aktiva ploché."""
  22      m = {}
  23      for a in sl.ASSETS:
  24          spot, perp = flat(n_bars)
  25          if a == "BTCUSDT" and events:
  26              for i, (sc, sh, pc) in events.items():
  27                  t = T0 + i * BAR
  28                  spot[t] = (sc, 10.0, 10.0 * sh)
  29                  perp[t] = (perp[t][0], pc)
  30          for i in drop_perp:
  31              perp.pop(T0 + i * BAR, None)
  32          m[a] = sl.prepare(spot, perp, fund or {})
  33      return m
  34  
  35  
  36  def test_features_use_only_current_and_previous_bar():
  37      m = market_with({10: (100.5, 0.8, 100.0)})
  38      f = {T: (sh, rs, rp) for T, sh, rs, rp in m["BTCUSDT"]["features"]}
  39      sh, rs, rp = f[T0 + 10 * BAR]
  40      assert sh == pytest.approx(0.8) and rs == pytest.approx(0.005) and rp == pytest.approx(0.0)
  41      assert T0 not in f  # bez předchozí svíčky žádný příznak
  42  
  43  
  44  def test_long_signal_enters_next_open_and_exits_after_hold():
  45      m = market_with({10: (100.5, 0.8, 100.0)})
  46      c = sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 1000 * BAR, 0.65, 15)
  47      assert len(c) == 1
  48      x = c[0]
  49      assert x["side"] == 1
  50      assert x["entry_ts"] == T0 + 11 * BAR
  51      assert x["exit_ts"] == T0 + 14 * BAR
  52      assert x["data_gap"] == 0
  53  
  54  
  55  def test_short_signal_mirror_and_thresholds():
  56      m = market_with({10: (99.5, 0.2, 100.0), 50: (99.5, 0.32, 100.0)})
  57      c65 = sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 1000 * BAR, 0.65, 15)
  58      c70 = sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 1000 * BAR, 0.70, 15)
  59      assert [x["side"] for x in c65] == [-1, -1]
  60      assert len(c70) == 1  # podíl 0,32 není < 0,30
  61  
  62  
  63  def test_perp_already_moved_blocks_signal():
  64      m = market_with({10: (100.5, 0.8, 100.2)})  # r_perp +0,2 % ≥ +0,1 %
  65      assert sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 1000 * BAR, 0.65, 15) == []
  66  
  67  
  68  def test_no_overlap_per_asset():
  69      # 1. obchod: signál 10, vstup 11, výstup 14. Signál 11 (vstup 12) během pozice ⇒ ignorován;
  70      # signál 13 má vstup 14 = výstup prvního ⇒ povolen.
  71      m = market_with({10: (100.5, 0.8, 100.0), 11: (101.0, 0.8, 100.0), 13: (100.5, 0.8, 100.0)})
  72      c = sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 1000 * BAR, 0.65, 15)
  73      assert [x["signal_ts"] for x in c] == [T0 + 10 * BAR, T0 + 13 * BAR]
  74      assert c[1]["entry_ts"] == c[0]["exit_ts"]
  75  
  76  
  77  def test_missing_entry_bar_drops_signal_and_missing_exit_flags_gap():
  78      m = market_with({10: (100.5, 0.8, 100.0)}, drop_perp=(11,))
  79      assert sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 1000 * BAR, 0.65, 15) == []
  80      m = market_with({10: (100.5, 0.8, 100.0)}, drop_perp=(14,))
  81      x = sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 1000 * BAR, 0.65, 15)[0]
  82      assert x["exit_ts"] == T0 + 15 * BAR and x["data_gap"] == 1
  83  
  84  
  85  def test_funding_only_strictly_inside_holding():
  86      # vstup 11*5m = 00:55, výstup 01:10 (15 min) ⇒ událost 01:00 uvnitř; 30 min držení ⇒ stejně jedna
  87      fund = {T0 + H: 0.001, T0: 0.5, T0 + 2 * H: 0.5}
  88      m = market_with({10: (100.5, 0.8, 100.0)}, fund=fund)
  89      x = sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 1000 * BAR, 0.65, 15)[0]
  90      assert x["funding_unit"] == pytest.approx(-0.001 * 100.0)  # long platí kladnou sazbu
  91      # událost přesně v čase vstupu se nezapočte
  92      m2 = market_with({11: (100.5, 0.8, 100.0)}, fund={T0 + H: 0.001})
  93      y = sl.candidates(m2["BTCUSDT"], "BTCUSDT", T0, T0 + 1000 * BAR, 0.65, 15)[0]
  94      assert y["entry_ts"] == T0 + H and y["funding_unit"] == 0.0
  95  
  96  
  97  def test_prefix_invariance():
  98      ev = {10: (100.5, 0.8, 100.0), 300: (99.5, 0.2, 100.0)}
  99      short = sl.candidates(market_with(ev, n_bars=1000)["BTCUSDT"], "BTCUSDT", T0, T0 + 900 * BAR, 0.65, 15)
 100      long_ = sl.candidates(market_with(ev, n_bars=3000)["BTCUSDT"], "BTCUSDT", T0, T0 + 900 * BAR, 0.65, 15)
 101      assert short == long_
 102  
 103  
 104  def test_costs_scale_and_equity_reconciles():
 105      ev = {10: (100.5, 0.8, 100.0), 300: (99.5, 0.2, 100.0)}
 106      m = market_with(ev, n_bars=2000)
 107      end = date(2021, 1, 6)
 108      costs = {}
 109      for mult in (1, 2, 3):
 110          trades, curve = sl.simulate(m, START, end, 0.65, 15, mult)
 111          costs[mult] = sum(t["costs"] for t in trades) / sum(t["notional"] for t in trades)
 112          assert curve[end] == pytest.approx(sl.START_EQUITY + sum(t["net_pnl"] for t in trades))
 113      assert costs[2] == pytest.approx(2 * costs[1]) and costs[3] == pytest.approx(3 * costs[1])
 114      # plochá cena ⇒ každý obchod ztratí právě round-trip náklady 2 × 0,115 %
 115      trades, _ = sl.simulate(m, START, end, 0.65, 15, 1)
 116      assert trades[0]["net_pnl"] == pytest.approx(-1000 * 2 * (sl.FEE + sl.SLIP))
 117  
 118  
 119  def test_exit_must_stay_inside_period():
 120      m = market_with({10: (100.5, 0.8, 100.0)})
 121      assert sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 13 * BAR, 0.65, 15) == []
 122  
 123  
 124  def test_neighbors_and_gap_audit():
 125      assert set(sl.neighbors(0.65, 15)) == {(0.65, 30), (0.70, 15)}
 126      m = market_with(drop_perp=(5, 6))
 127      a = sl.gap_audit(m["BTCUSDT"])
 128      assert a["perp_missing_5m"] == 2 and a["spot_only"] == 2
 129  
 130  
 131  # ---- oponentura ChatGPT kolo 2, bod G a společné opravy (B&H funding, nedefinované DSR, latence) ----
 132  def test_G_overnight_position_enters_daily_mtm():
 133      i_sig = 24 * 12 - 3  # signál 23:45, vstup 23:50, výstup 00:05 dalšího dne
 134      m = market_with({i_sig: (100.5, 0.8, 100.0)}, n_bars=3 * 288)
 135      t_last = T0 + (24 * 12 - 1) * BAR  # svíčka 23:55 dne 1
 136      m["BTCUSDT"]["perp"][t_last] = (100.0, 110.0)  # close 23:55 = 110
 137      trades, curve = sl.simulate(m, START, date(2021, 1, 2), 0.65, 15, 1)
 138      tr = trades[0]
 139      assert tr["entry_ts"] < T0 + sl.DAY_MS < tr["exit_ts"]
 140      expected = sl.START_EQUITY + tr["qty"] * (110.0 - 100.0) - tr["cost_in"]
 141      assert curve[START] == pytest.approx(expected)
 142      assert curve[date(2021, 1, 2)] == pytest.approx(sl.START_EQUITY + tr["net_pnl"])
 143  
 144  
 145  def test_G_exit_delay_is_bounded():
 146      # mezera 30 min ⇒ první dostupný open, data_gap 1
 147      m = market_with({10: (100.5, 0.8, 100.0)}, drop_perp=range(14, 20))
 148      x = sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 1000 * BAR, 0.65, 15)[0]
 149      assert x["exit_ts"] == T0 + 20 * BAR and x["data_gap"] == 1
 150      # mezera > 60 min ⇒ DATA_GAP 2, cena = poslední close před plánovaným výstupem, čas = plán + 60 min
 151      m = market_with({10: (100.5, 0.8, 100.0)}, drop_perp=range(14, 40))
 152      m["BTCUSDT"]["perp"][T0 + 13 * BAR] = (100.0, 97.0)
 153      x = sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 1000 * BAR, 0.65, 15)[0]
 154      assert x["data_gap"] == 2 and x["exit"] == 97.0 and x["exit_ts"] == T0 + 14 * BAR + sl.MAX_EXIT_DELAY_MS
 155  
 156  
 157  def test_G_no_exit_beyond_period_end_time_based():
 158      m = market_with({10: (100.5, 0.8, 100.0)})
 159      end = T0 + 14 * BAR + sl.MAX_EXIT_DELAY_MS  # plán + max. zpoždění = konec ⇒ nebrat
 160      assert sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, end, 0.65, 15) == []
 161      assert len(sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, end + BAR, 0.65, 15)) == 1
 162  
 163  
 164  def test_G_simultaneous_entries_independent_of_symbol_order(monkeypatch):
 165      def mk():
 166          m = {}
 167          for a in sl.ASSETS:
 168              spot, perp = flat()
 169              t = T0 + 10 * BAR
 170              spot[t] = (100.5, 10.0, 8.0)
 171              perp[T0 + 14 * BAR] = (101.0 if a == "ETHUSDT" else 99.0, 100.0)
 172              m[a] = sl.prepare(spot, perp, {})
 173          return m
 174      m = mk()
 175      a1, _ = sl.simulate(m, START, date(2021, 1, 6), 0.65, 15, 1)
 176      monkeypatch.setattr(sl, "ASSETS", tuple(reversed(sl.ASSETS)))
 177      a2, _ = sl.simulate(m, START, date(2021, 1, 6), 0.65, 15, 1)
 178      key = lambda t: (t["asset"], t["notional"], round(t["net_pnl"], 9))
 179      assert sorted(map(key, a1)) == sorted(map(key, a2))
 180      assert all(t["notional"] == pytest.approx(1000.0) for t in a1) and len(a1) == 3
 181  
 182  
 183  def test_latency_sensitivity_enters_one_bar_later():
 184      m = market_with({10: (100.5, 0.8, 100.0)})
 185      x = sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 1000 * BAR, 0.65, 15, delay_bars=1)[0]
 186      assert x["entry_ts"] == T0 + 12 * BAR and x["exit_ts"] == T0 + 15 * BAR
 187  
 188  
 189  def test_buy_hold_accounts_funding_sign():
 190      res = {}
 191      for r in (0.0, 0.01, -0.01):
 192          fund = {T0 + k * 8 * H: r for k in range(1, 6)}
 193          m = market_with(n_bars=2000, fund=fund)
 194          res[r] = sl.buy_hold(m, START, date(2021, 1, 6), 1)
 195      assert res[0.01]["net_pnl"] < res[0.0]["net_pnl"] < res[-0.01]["net_pnl"]
 196      assert res[0.01]["funding"] == pytest.approx(-0.01 * sl.START_EQUITY * (1 - (sl.FEE + sl.SLIP)) * 5)
 197  
 198  
 199  def test_undefined_dsr_is_null_not_zero():
 200      out = sl.safe_dsr([0.0] * 731, 159, 0.5)
 201      assert out["dsr"] is None and out["undefined_reason"]
 202  
 203  
 204  # ---- oponentura ChatGPT kolo 3 ----
 205  def _overnight_market(fund=None, drop=()):
 206      i_sig = 24 * 12 - 3  # signál 23:45, vstup 23:50, výstup 00:05
 207      m = market_with({i_sig: (100.5, 0.8, 100.0)}, n_bars=3 * 288, fund=fund, drop_perp=drop)
 208      return m
 209  
 210  
 211  def test_K3_2_midnight_funding_belongs_to_new_day_consistently():
 212      m = _overnight_market(fund={T0 + sl.DAY_MS: 0.01})
 213      trades, curve = sl.simulate(m, START, date(2021, 1, 2), 0.65, 15, 1)
 214      tr = trades[0]
 215      assert curve[START] == pytest.approx(9998.85)  # ocenění před událostmi v 00:00
 216      assert curve[date(2021, 1, 2)] == pytest.approx(sl.START_EQUITY + tr["net_pnl"])
 217      assert tr["funding"] == pytest.approx(-0.01 * tr["qty"] * 100.0)
 218      # benchmark se stejnou konvencí: funding v 00:00 dne 2 se projeví až ve dni 2
 219      bh_m = market_with(n_bars=3 * 288, fund={T0 + sl.DAY_MS: 0.01})
 220      b1 = sl.buy_hold(bh_m, START, START, 1)
 221      b2 = sl.buy_hold(bh_m, START, date(2021, 1, 2), 1)
 222      assert b1["funding"] == 0.0 and b2["funding"] < 0
 223  
 224  
 225  def test_K3_2_exit_exactly_at_midnight_and_entry_at_midnight():
 226      # vstup 23:45, výstup přesně 00:00 (15 min): den 1 = ocenění otevřené pozice, realizace ve dni 2
 227      i_sig = 24 * 12 - 4
 228      m = market_with({i_sig: (100.5, 0.8, 100.0)}, n_bars=3 * 288)
 229      m["BTCUSDT"]["perp"][T0 + (24 * 12 - 1) * BAR] = (100.0, 105.0)
 230      trades, curve = sl.simulate(m, START, date(2021, 1, 2), 0.65, 15, 1)
 231      tr = trades[0]
 232      assert tr["exit_ts"] == T0 + sl.DAY_MS
 233      assert curve[START] == pytest.approx(sl.START_EQUITY + tr["qty"] * 5.0 - tr["cost_in"])
 234      assert curve[date(2021, 1, 2)] == pytest.approx(sl.START_EQUITY + tr["net_pnl"])
 235      # vstup přesně v 00:00 patří novému dni: den 1 beze změny
 236      m2 = market_with({24 * 12 - 1: (100.5, 0.8, 100.0)}, n_bars=3 * 288)
 237      t2, c2 = sl.simulate(m2, START, date(2021, 1, 2), 0.65, 15, 1)
 238      assert t2[0]["entry_ts"] == T0 + sl.DAY_MS and c2[START] == sl.START_EQUITY
 239  
 240  
 241  def test_K3_3_day_close_never_uses_future_price():
 242      perp = {T0 + sl.DAY_MS + k * BAR: (100.0, 100.0 if k == 0 else 200.0) for k in range(2 * 288)}
 243      m = sl.prepare({}, perp, {})
 244      assert sl.day_close(m, date(2021, 1, 1)) is None
 245      assert sl.day_close(sl.prepare({}, {}, {}), date(2021, 1, 1)) is None
 246      p, age = sl.day_close(m, date(2021, 1, 2))
 247      assert p == 200.0 and age == 0
 248  
 249  
 250  def test_K3_3_benchmark_asset_unavailable_at_start_is_cash():
 251      m = market_with(n_bars=2000)
 252      late = {t + 3 * sl.DAY_MS: v for t, v in m["XRPUSDT"]["perp"].items()}  # první svíčka až za koncem období
 253      m["XRPUSDT"] = sl.prepare(m["XRPUSDT"]["spot"], late, {})
 254      b = sl.buy_hold(m, START, date(2021, 1, 2), 1)
 255      assert b["unavailable_at_start"] == ["XRPUSDT"]
 256      # 2/3 v aktivech (ploché ceny) − náklady, 1/3 hotovost
 257      c = sl.FEE + sl.SLIP
 258      assert b["net_pnl"] == pytest.approx(-(2 / 3) * sl.START_EQUITY * (1 - (1 - c) ** 2), abs=1e-3)
 259  
 260  
 261  def test_K3_4_funding_price_fallback_is_flagged_and_aged():
 262      m = _overnight_market(fund={T0 + sl.DAY_MS: 0.01}, drop=(288,))
 263      x = sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 3 * sl.DAY_MS, 0.65, 15)[0]
 264      assert x["funding_price_fallbacks"] == 1 and x["funding_price_max_age_min"] == 0.0
 265      assert x["unevaluable"] == 0
 266      # náhrada starší než 60 min ⇒ nehodnotitelné: svíčky 23:55–01:00 chybí, výstup zpožděn na 01:05 (data_gap 1),
 267      # funding v 01:00 (1h interval) by se počítal z close 23:55 ⇒ stáří 65 min
 268      fund = {T0 + sl.DAY_MS: (0.01, 1.0), T0 + sl.DAY_MS + H: (0.01, 1.0)}
 269      m = _overnight_market(fund=fund, drop=range(287, 301))
 270      x = sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 3 * sl.DAY_MS, 0.65, 15)[0]
 271      assert x["data_gap"] == 1 and x["exit_ts"] == T0 + sl.DAY_MS + H + BAR
 272      assert x["funding_price_fallbacks"] == 2 and x["funding_price_max_age_min"] == 65.0 and x["unevaluable"] == 1
 273  
 274  
 275  def test_K3_4_missing_funding_event_is_flagged_not_zero():
 276      # interval 8 h, ale událost 00:00 chybí (je jen 16:00 předchozího dne a 08:00) ⇒ mezera v úplnosti
 277      fund = {T0 + 16 * H: (0.0001, 8.0), T0 + 32 * H: (0.0001, 8.0)}
 278      m = _overnight_market(fund=fund)
 279      x = sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 3 * sl.DAY_MS, 0.65, 15)[0]
 280      assert x["funding_gaps"] == 1 and x["funding_unit"] == 0.0
 281      ok = _overnight_market(fund={T0 + 16 * H: 0.0001, T0 + 24 * H: 0.0001, T0 + 32 * H: 0.0001})
 282      y = sl.candidates(ok["BTCUSDT"], "BTCUSDT", T0, T0 + 3 * sl.DAY_MS, 0.65, 15)[0]
 283      assert y["funding_gaps"] == 0 and y["funding_unit"] != 0.0
````

## E. Skutečný výstup testů
CI GitHub Actions: PR #29 run 42254530343 → `37 passed in 0.58s`, `RUN_REQUEST chybí - jen testy`; PR #30 run 42254846457 → `31 passed in 0.29s`, `RUN_REQUEST chybí - jen testy`.
Lokálně `pytest -v` PR #29 (+ DSR):
````
test_funding_dispersion.py::test_selection_longs_lowest_shorts_highest PASSED [  2%]
test_funding_dispersion.py::test_signal_uses_only_settled_rates_up_to_decision PASSED [  5%]
test_funding_dispersion.py::test_prefix_invariance_of_decisions PASSED [  8%]
test_funding_dispersion.py::test_funding_cashflow_sign_and_boundaries PASSED [ 10%]
test_funding_dispersion.py::test_costs_scale_linearly PASSED       [ 13%]
test_funding_dispersion.py::test_short_leg_liquidation_at_double_price PASSED [ 16%]
test_funding_dispersion.py::test_long_short_pnl_and_no_overlap PASSED [ 18%]
test_funding_dispersion.py::test_skips_week_when_too_few_eligible PASSED [ 21%]
test_funding_dispersion.py::test_buy_hold_and_evaluate_shapes PASSED [ 24%]
test_funding_dispersion.py::test_funding_exactly_at_entry_and_exit_is_excluded PASSED [ 27%]
test_funding_dispersion.py::test_funding_one_hour_inside_edges_is_included_once PASSED [ 29%]
test_funding_dispersion.py::test_changing_future_data_does_not_change_earlier_decisions_weights_fills PASSED [ 32%]
test_funding_dispersion.py::test_costs_charged_on_all_four_legs_entry_and_exit PASSED [ 35%]
test_funding_dispersion.py::test_vol_matched_benchmark_info PASSED [ 37%]
test_funding_dispersion.py::test_R1_repro_sparse_data_is_not_eligible PASSED [ 40%]
test_funding_dispersion.py::test_R1_missing_funding_event_inside_window_makes_ineligible_not_zero PASSED [ 43%]
test_funding_dispersion.py::test_R1_interval_change_8h_4h_1h_is_continuous PASSED [ 45%]
test_funding_dispersion.py::test_R1_duplicate_after_normalization PASSED [ 48%]
test_funding_dispersion.py::test_R2_benchmark_accounts_funding_sign PASSED [ 51%]
test_funding_dispersion.py::test_R3_gap_through_liquidation_at_exit_open PASSED [ 54%]
test_funding_dispersion.py::test_R3_high_of_exit_hour_is_not_used PASSED [ 56%]
test_funding_dispersion.py::test_R4_no_trades_still_writes_results_with_null_dsr PASSED [ 59%]
test_funding_dispersion.py::test_R4_constant_returns_dsr_undefined PASSED [ 62%]
test_funding_dispersion.py::test_B_basket_metrics_aggregate_four_legs PASSED [ 64%]
test_funding_dispersion.py::test_D_decision_after_publication_time PASSED [ 67%]
test_funding_dispersion.py::test_E_edge_funding_impact_is_quantified PASSED [ 70%]
test_funding_dispersion.py::test_K3_1_missing_future_entry_bar_does_not_change_selection PASSED [ 72%]
test_funding_dispersion.py::test_K3_eligibility_uses_only_bars_closed_by_decision PASSED [ 75%]
test_funding_dispersion.py::test_K3_data_audit_reports_interval_transitions_for_both_semantics PASSED [ 78%]
test_funding_dispersion.py::test_K3_audit_only_mode_writes_audit_without_performance PASSED [ 81%]
test_deflated_sharpe.py::test_paper_numeric_example PASSED         [ 83%]
test_deflated_sharpe.py::test_single_trial_is_psr_vs_zero PASSED   [ 86%]
test_deflated_sharpe.py::test_normal_psr_closed_form PASSED        [ 89%]
test_deflated_sharpe.py::test_dsr_decreases_with_trials_and_variance PASSED [ 91%]
test_deflated_sharpe.py::test_negative_skew_and_fat_tails_lower_psr PASSED [ 94%]
test_deflated_sharpe.py::test_moments_and_from_returns PASSED      [ 97%]
test_deflated_sharpe.py::test_var_from_trials_and_errors PASSED    [100%]
````
Lokálně `pytest -v` PR #30 (+ DSR):
````
test_spot_led.py::test_features_use_only_current_and_previous_bar PASSED [  3%]
test_spot_led.py::test_long_signal_enters_next_open_and_exits_after_hold PASSED [  6%]
test_spot_led.py::test_short_signal_mirror_and_thresholds PASSED   [  9%]
test_spot_led.py::test_perp_already_moved_blocks_signal PASSED     [ 12%]
test_spot_led.py::test_no_overlap_per_asset PASSED                 [ 16%]
test_spot_led.py::test_missing_entry_bar_drops_signal_and_missing_exit_flags_gap PASSED [ 19%]
test_spot_led.py::test_funding_only_strictly_inside_holding PASSED [ 22%]
test_spot_led.py::test_prefix_invariance PASSED                    [ 25%]
test_spot_led.py::test_costs_scale_and_equity_reconciles PASSED    [ 29%]
test_spot_led.py::test_exit_must_stay_inside_period PASSED         [ 32%]
test_spot_led.py::test_neighbors_and_gap_audit PASSED              [ 35%]
test_spot_led.py::test_G_overnight_position_enters_daily_mtm PASSED [ 38%]
test_spot_led.py::test_G_exit_delay_is_bounded PASSED              [ 41%]
test_spot_led.py::test_G_no_exit_beyond_period_end_time_based PASSED [ 45%]
test_spot_led.py::test_G_simultaneous_entries_independent_of_symbol_order PASSED [ 48%]
test_spot_led.py::test_latency_sensitivity_enters_one_bar_later PASSED [ 51%]
test_spot_led.py::test_buy_hold_accounts_funding_sign PASSED       [ 54%]
test_spot_led.py::test_undefined_dsr_is_null_not_zero PASSED       [ 58%]
test_spot_led.py::test_K3_2_midnight_funding_belongs_to_new_day_consistently PASSED [ 61%]
test_spot_led.py::test_K3_2_exit_exactly_at_midnight_and_entry_at_midnight PASSED [ 64%]
test_spot_led.py::test_K3_3_day_close_never_uses_future_price PASSED [ 67%]
test_spot_led.py::test_K3_3_benchmark_asset_unavailable_at_start_is_cash PASSED [ 70%]
test_spot_led.py::test_K3_4_funding_price_fallback_is_flagged_and_aged PASSED [ 74%]
test_spot_led.py::test_K3_4_missing_funding_event_is_flagged_not_zero PASSED [ 77%]
test_deflated_sharpe.py::test_paper_numeric_example PASSED         [ 80%]
test_deflated_sharpe.py::test_single_trial_is_psr_vs_zero PASSED   [ 83%]
test_deflated_sharpe.py::test_normal_psr_closed_form PASSED        [ 87%]
test_deflated_sharpe.py::test_dsr_decreases_with_trials_and_variance PASSED [ 90%]
test_deflated_sharpe.py::test_negative_skew_and_fat_tails_lower_psr PASSED [ 93%]
test_deflated_sharpe.py::test_moments_and_from_returns PASSED      [ 96%]
test_deflated_sharpe.py::test_var_from_trials_and_errors PASSED    [100%]
````

## F. .github/workflows/funding-dispersion.yml (`8a008b6`)
````yaml
name: Funding dispersion 8 perps backtest (PAPER research, public data only)
# Jen výzkumná větev. Žádné secrets, žádný Render, žádné objednávky.
# Backtest se spouští jen commitem research/funding_dispersion/RUN_REQUEST (nejdřív 2026-11-07 UTC, denní limit hypotéz).
on:
  push:
    branches: ["research/funding-dispersion-*"]
    paths:
      - "research/funding_dispersion/RUN_REQUEST"
      - "research/funding_dispersion/run.py"
      - "tests/test_funding_dispersion.py"
  workflow_dispatch:
permissions:
  contents: write
jobs:
  backtest:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: pip install pytest
      - name: Mechanics tests (synthetic, not profitability evidence)
        run: python -m pytest -q -p no:cacheprovider tests/test_funding_dispersion.py tests/test_deflated_sharpe.py
      - name: Backtest per PROTOCOL.md (only when RUN_REQUEST exists)
        run: |
          set -o pipefail
          if [ ! -f research/funding_dispersion/RUN_REQUEST ]; then echo "RUN_REQUEST chybí - jen testy"; exit 0; fi
          # RUN_REQUEST začínající "AUDIT" = jen kontrola dat (data_audit.json), bez výpočtu výkonnosti (dodatek 3)
          if head -1 research/funding_dispersion/RUN_REQUEST | grep -q '^AUDIT'; then MODE=--audit-only; else MODE=; fi
          python -m research.funding_dispersion.run --cache /tmp/vision-fd --outdir research/funding_dispersion $MODE | tee summary.txt
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: funding-dispersion
          path: research/funding_dispersion/
      - name: Commit results to this research branch
        if: success()
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898333+github-actions[bot]@users.noreply.github.com"
          git add research/funding_dispersion/
          git diff --cached --quiet && exit 0
          git commit -m "Funding dispersion: backtest results (run ${GITHUB_RUN_ID}) [skip ci]"
          git push origin HEAD:${GITHUB_REF_NAME}
````
