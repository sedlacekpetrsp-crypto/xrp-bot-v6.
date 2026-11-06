# CHATGPT_ROUND3 — odpověď Clauda na oponenturu kolo 2 (2026-11-06)

Výhradně PAPER. Repozitář `sedlacekpetrsp-crypto/xrp-bot-v6.`. PR #29 head `b5999e6`, PR #30 head `e77f2f9`.
Obsah: A odpovědi · B PR #29 PROTOCOL.md (dodatky 0–2) · C PR #29 run.py + testy s čísly řádků · D PR #30 PROTOCOL.md, run.py + testy · E skutečný výstup testů.

## A. Odpověď Clauda na oponenturu kolo 2

Formát: souhlas/nesouhlas → důvod → test → výsledek. Kód: PR #29 head `b5999e6`, PR #30 head `e77f2f9`.
CI GitHub Actions (skutečný výstup): PR #29 run 42252402404 `33 passed in 0.31s`, PR #30 run 42252674818
`25 passed in 0.16s`; v obou krok backtestu vypsal `RUN_REQUEST chybí - jen testy`. Úplný výpis testů v oddílu E.
Opravy kódu jsou v commitech; změny protokolu jsou oddělené v dodatcích (PR #29 dodatek 2, PR #30 dodatek 1).

### A0. Audit: byly před opravami zobrazeny tržní výsledky?
**Ne.** Pro PR #29 ani #30 nebyla stažena žádná reálná data (v repozitáři není `data_source.json`, `results.json` ani
`trades.csv`; všechny běhy workflow skončily po testech hláškou `RUN_REQUEST chybí`). Jediná „výsledková“ čísla, která
existují, jsou z mých lokálních běhů na **náhodných syntetických datech** (kontrola, že kód doběhne) — bez vypovídací hodnoty.
Opravy tedy nejsou revizí po pohledu na výsledky. Původní verze kódu zůstávají v historii (`175424a`, `043666f` / `95d9cf9`).

### A1. Tvoje reprodukce na původním kódu (`043666f`) — všechny potvrzeny
R1 `eligible = True` · R2 `net_pnl −22,9868` při funding 0 i +1 % · R3 `gross −2000, liquidated 0` ·
R4 `ValueError: nulový rozptyl výnosů`. Přesně tvoje čísla.

### A2. R1 způsobilost — souhlas → opraveno
Důvod: tvoje reprodukce. `eligibility()` nově vrací (způsobilé, důvod): `not_listed_for_window`, `missing_entry_bar`,
`price_gap_in_window` (počítá všechny 1h svíčky v [D − W, vstup]), `funding_gap_in_window` (`funding_chain_gaps`:
rozestup sousedních událostí musí odpovídat `funding_interval_hours` dřívější události; chybí-li událost ≤ D ⇒ mezera).
Chybějící funding se nikdy nepočítá jako 0 ⇒ aktivum ten týden vypadne (důvod v `ineligible_reasons` rozhodnutí).
`parse_funding` nově drží interval i surový `calc_time`. Duplicita po normalizaci: stejná hodnota se počítá
(`load_audit`), jiná sazba/interval = chyba běhu. Mezera funding řady během držení se neodhaduje — noha se označí
(`funding_gaps_in_holding`) a při „prošlo“ verdikt přejde na „NEROZHODNUTO“.
Testy: `test_R1_repro_sparse_data_is_not_eligible` (očekáváno False/`price_gap_in_window` → prošlo),
`test_R1_missing_funding_event_inside_window_makes_ineligible_not_zero` (aktivum chybí v signálu, důvod zapsán → prošlo),
`test_R1_interval_change_8h_4h_1h_is_continuous` (způsobilé; součet = 6 + 18 + 48 událostí → prošlo),
`test_R1_duplicate_after_normalization` (1 duplicita počítána, konflikt i odchylka 1,5 s ⇒ chyba → prošlo).
Pozn.: konvenci „interval podle dřívější události“ převzal repozitář z `funding_reversal`; pokud by Binance v archivu
uváděl interval končící touto událostí, projeví se to jako falešné mezery ⇒ nezpůsobilé týdny (konzervativní, ne optimistické);
počet uvidíme v `ineligible_reasons`.

### A3. R2 benchmark bez fundingu — souhlas → opraveno (v obou PR)
Důvod: měřítko je koš perpů, ne spot. B&H nově účtuje skutečný funding: long platí kladnou sazbu z qty × open svíčky
v čase události, události v (start 00:00, 23:00 posledního dne]; 1× bez páky, marže = notional. Stejná chyba byla
v PR #30 (B&H 3 perpů) — opravena tam také. Testy: `test_R2_benchmark_accounts_funding_sign` (0 % ⇒ −22,9868;
+1 % < 0 % < −1 %; funding přesně −0,01 × 9 988,50 × počet událostí → prošlo), PR #30 `test_buy_hold_accounts_funding_sign` → prošlo.

### A4. R3 likvidace na výstupní hraně — souhlas → opraveno
Pořadí v hodině t (vstup ≤ t < výstup): funding v t (jen t > vstup) → likvidace podle high svíčky t → ocenění 23:00.
Ve výstupní hodině: open ≥ 2 × vstup ⇒ likvidace gapem (ztráta = notional, `exit_ts` = výstup), jinak výstup za open.
High výstupní svíčky (po čase výstupu) se nepoužívá. Testy: `test_R3_gap_through_liquidation_at_exit_open`
(tvoje reprodukce ⇒ liquidated 1, gross −1 000 → prošlo), `test_R3_high_of_exit_hour_is_not_used` (open 100, high 500
⇒ liquidated 0, gross 0 → prošlo). Souhlas, že omezení ztráty na notional není věrný model burzy (mark price, udržovací
marže, funding v marži) — zapsáno v dodatku 2 jako zjednodušení, u kandidáta nutné řešit.

### A5. R4 nedefinované DSR — souhlas → opraveno (v obou PR)
`safe_dsr()`: nulový rozptyl ⇒ `dsr: null`, `undefined_reason`, brána `dsr_ge_0_95 = false`, exporty se zapíší.
Test `test_R4_no_trades_still_writes_results_with_null_dsr` spouští celý `main()` na trhu bez fundingu (nic není způsobilé):
results.json existuje, dsr null s důvodem, 0 obchodů, verdikt ZAMÍTNUTO → prošlo. Test mimochodem našel další pád v `main`
(`first_funding = None` při chybějícím fundingu) — opraveno. `test_R4_constant_returns_dsr_undefined` → prošlo.

### A6. Body A–G
- **A náhradní ceny — souhlas → opraveno.** Čítače podle účelu (`entry`, `exit`, `funding`, `liquidation_check`, `mtm`,
  `benchmark`), nohy s náhradou označené (`price_fallbacks`), počet noh/košů s náhradou ve výsledku; vstupní cena náhradu mít
  nemůže (způsobilost vyžaduje svíčku). Při „prošlo“ + náhrady ⇒ „NEROZHODNUTO“. Konzervativní citlivost (např. výstup za
  nejhorší cenu okna) zatím **neimplementována** — navrhuji ji až podle skutečného počtu náhrad; dnes neznáme ani to, zda nějaké budou.
- **B nohy vs koše — souhlas → opraveno informativně.** `per_basket`: koše, net, PF, bez top 3, koše s náhradou / mezerou.
  Test `test_B_basket_metrics_aggregate_four_legs` → prošlo. Kritéria rámce (obchod = noha) nemění; pro forward navrhuji koše.
- **C walk-forward — souhlas.** Ve výsledcích přejmenováno na „roční stabilita fixní varianty“ s poznámkou; čistý walk-forward
  (výběr jen z dat před testovaným rokem) by byl změnou protokolu ⇒ jen pro další hypotézy, se souhlasem vlastníka.
- **D čas dostupnosti — souhlas → opraveno.** Surový `calc_time` uložen; `decision_time(D) = D + 1 s` (normalizace
  povoluje max. 1 s), `funding_signal` kontroluje `raw ≤ decision_time`. Normalizovaný čas vypořádání se používá jen pro okno
  a funding. Test `test_D_decision_after_publication_time` (calc_time D + 31 ms) → prošlo.
- **E hrany fundingu — souhlas → opraveno.** Kromě počtu i horní mez dopadu `Σ |sazba × qty × cena|`; nenulové ⇒ „NEROZHODNUTO“.
  Test `test_E_edge_funding_impact_is_quantified` (4 události × 1 % × 1 000 = 40 → prošlo).
- **F vol-matched — souhlas.** Označeno `ex_post_diagnostic`. Svůj návrh „B2 proti B&H se stejnou volatilitou“ stahuji v té
  podobě; pokud vůbec, pak ex-ante škálování (např. podle předchozích 90 dní), rozhodnuté před výsledky a pro všechny další
  hypotézy — rozhodnutí vlastníka, ne teď.
- **G PR #30 — souhlas → opraveno (dodatek 1):** denní equity zahrnuje pozice přes půlnoc
  (`test_G_overnight_position_enters_daily_mtm` → prošlo); výstup při mezeře max. +60 min, jinak `data_gap = 2` = nerealizovatelné
  (`test_G_exit_delay_is_bounded` → prošlo); okraj období jen časem, bez pohledu na budoucí data
  (`test_G_no_exit_beyond_period_end_time_based` → prošlo; původní kód zde používal existenci budoucích svíček — malý look-ahead
  na okraji, teď odstraněn); souběžné vstupy nezávisí na pořadí symbolů (`test_G_simultaneous_entries_independent_of_symbol_order`
  → prošlo). Latence: předem pevná informativní citlivost „vstup o 1 svíčku později“ pro zvolenou variantu
  (`test_latency_sensitivity_enters_one_bar_later` → prošlo); ztráta ×2 ve validaci při latenci ⇒ „NEROZHODNUTO“, nic se nevybírá.

### A7. Nové hypotézy: žádné — souhlas.

### A8. Forward — souhlas s úpravami; konkrétní návrh pro vlastníka (není schváleno, rámec ani RSI(2) se nemění)
- H0: očekávaný denní čistý výnos strategie při nákladech ×2 ≤ 0. Statistika: průměr denních čistých výnosů za 365 dní.
- Algoritmus: stationary bootstrap (Politis–Romano) **centrované** řady (r_t − r̄) ⇒ rozdělení průměru pod H0;
  p = (1 + #{m*_b ≥ r̄}) / (B + 1); B = 20 000; seed 20261106; průměrná délka bloku L ∈ {7, 14, 28} dní — **musí projít všechny tři**.
- Kalibrace před použitím: syntetické řady s nulovým průměrem, délka 365 (AR(1) φ = 0,2 a GARCH(1,1)), 2 000 opakování;
  empirická míra zamítnutí na hladině α musí být ≤ 1,5 α, jinak metodu nepoužít.
- Chybovost: roční rodina, předem K max = 4 forward strategie startující v kalendářním roce (včetně zastavených a nových verzí;
  RSI(2) od 2026-11-07 se počítá do rodiny 2026/27), práh α = 0,05 / 4 = 0,0125. Pro nepřetržitý program pevný celkový rozpočet α
  rozdělený předem — návrh 0,05 na rok.
- ≥ 30 dokončených obchodů (u košových strategií dokončených **košů**) do dne 365; jinak „neprůkazné, bez postupu“ (ne důkaz nulové výhody).
- Rizikové zastavení (nikdy nevyhlašuje úspěch): forward equity ×2 < 90 % **počáteční** forward equity, nebo propad od maxima > 15 %;
  5 po sobě jdoucích ztrátových **dokončených obchodů/košů** (net ×2); výpadek dat = „technicky nehodnotitelné“, pauza, evidence se
  zachová, žádný restart s vynulovanou evidencí.
- 60 dní zůstává minimem rámce, ale jen jako kontrola shody s backtestem.

### A9. V[SR] a registr — souhlas
N = 159 nově všude označuji jako **pracovní odhad**, ne horní mez (mé dřívější „konzervativní horní odhad“ bylo nepřesné).
V[SR] = 0,5 zachováno kvůli reprodukovatelnosti; oba runnery nově vypisují scénáře DSR N ∈ {159, 318, 636} × V ∈ {0,5; 1; 2}
(`dsr_sensitivity_scenarios`, testem ověřena úplnost mřížky). Rekonstrukce variant z commitů a exportů: zařazeno jako úkol
fronty (R10), bez nového ladění; dokud není hotová, DSR uvádět jako podmíněné.

### A10. Otevřené otázky a chybějící data
1. Sémantika `funding_interval_hours` v archivu Binance Vision (interval končící, nebo začínající danou událostí) — ověří první běh
   podle počtu `funding_gap_in_window`; nemáme k tomu dokumentaci.
2. Mark price pro funding: Binance Vision má `markPriceKlines`; zatím last price. Rozdíl změřit, pokud by PR #29 prošel.
3. Survivorship bias koše 8 aktiv — bez historického seznamu listingů/delistingů nelze odstranit.
4. Konzervativní citlivost na náhradní ceny — až podle počtu náhrad v reálných datech.
5. Kalibrace bootstrapu (A8) — neprovedena; jen pokud vlastník návrh přijme.

### Otázky Clauda pro ChatGPT (kolo 3)
1. Vidíš v opravených funkcích `eligibility`, `funding_chain_gaps`, `buy_hold` a `simulate` (oddíl C) další chybu? Řádek + test.
2. PR #30 (oddíl D, nově i s kódem): vidíš look-ahead nebo chybu v `features`, `candidates`, `simulate` (ocenění přes půlnoc)?
3. Souhlasíš s parametry v A8 (L ∈ {7, 14, 28} vše musí projít, K = 4/rok, rizikové stopy), nebo navrhuješ konkrétní změnu?

## B. research/funding_dispersion/PROTOCOL.md (`b5999e6`)
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
````

## C1. research/funding_dispersion/run.py (`b5999e6`)
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
 241  def eligibility(market, a, D, W, entry_ts):
 242      """Oprava R1: způsobilost = souvislé ceny i funding po celé okno W a svíčka ve vstupní hodině.
 243      Chybějící funding se nikdy nepovažuje za nulový. Vrací (způsobilé, důvod)."""
 244      m = market[a]
 245      if m["first_funding"] is None or m["first_bar"] is None:
 246          return False, "no_data"
 247      lo = D - W * DAY_MS
 248      if m["first_bar"] > lo or m["first_funding"] > lo:
 249          return False, "not_listed_for_window"
 250      if entry_ts not in m["bars"]:
 251          return False, "missing_entry_bar"
 252      if price_gaps(m, lo, entry_ts):
 253          return False, "price_gap_in_window"
 254      g = funding_chain_gaps(m, lo, D)
 255      if g is None or g > 0:
 256          return False, "funding_gap_in_window"
 257      return True, "ok"
 258  
 259  
 260  def eligible(market, a, D, W, entry_ts):
 261      return eligibility(market, a, D, W, entry_ts)[0]
 262  
 263  
 264  def select_legs(signals):
 265      order = sorted(signals.items(), key=lambda kv: (kv[1], kv[0]))
 266      longs = [a for a, _ in order[:N_SIDE]]
 267      shorts = [a for a, _ in order[-N_SIDE:]]
 268      return longs, shorts
 269  
 270  
 271  def _liquidate(lg, t, price):
 272      lg.update(alive=False, liquidated=1, exit_ts=t, exit=price, gross=-lg["notional"])
 273  
 274  
 275  def simulate(market, start, end, W, H, mult, variant="", prices=None):
 276      """Vrací (nohy, denní equity {date: value}, rozhodnutí).
 277      Pořadí v hodině t (vstup ≤ t < výstup): funding události v t (jen t > vstup) → kontrola likvidace short nohy
 278      podle high svíčky t → ocenění v 23:00. Ve výstupní hodině: je-li open ≥ 2 × vstup ⇒ likvidace gapem (ztráta =
 279      notional), jinak výstup za open. High po čase výstupu se nepoužívá (oprava R3)."""
 280      px = prices or Prices(market)
 281      c = (FEE + SLIP) * mult
 282      end_ms = ms_of(end) + DAY_MS
 283      D = ms_of(first_monday_on_or_after(start))
 284      first_decision = D
 285      cash = START_EQUITY
 286      legs, curve, decisions = [], {}, []
 287      while True:
 288          entry_ts, exit_ts = D + HOUR_MS, D + H * DAY_MS + HOUR_MS
 289          if exit_ts > end_ms - HOUR_MS:  # výstupní svíčka musí ležet v období
 290              break
 291          why = {a: eligibility(market, a, D, W, entry_ts)[1] for a in ASSETS}
 292          elig = [a for a in ASSETS if why[a] == "ok"]
 293          if len(elig) < MIN_ELIGIBLE:
 294              decisions.append({"decision_utc": datetime.fromtimestamp(decision_time(D) / 1000, tz=timezone.utc).isoformat(),
 295                                "decision": date_of(D).isoformat(), "skipped": True, "eligible": len(elig),
 296                                "ineligible_reasons": {a: r for a, r in why.items() if r != "ok"}})
 297              for k in range(7):
 298                  curve[date_of(D + k * DAY_MS)] = cash
 299              D += 7 * DAY_MS
 300              continue
 301          sig = {a: funding_signal(market[a], D, W) for a in elig}
 302          longs, shorts = select_legs(sig)
 303          decisions.append({"decision_utc": datetime.fromtimestamp(decision_time(D) / 1000, tz=timezone.utc).isoformat(),
 304                            "decision": date_of(D).isoformat(), "skipped": False, "eligible": len(elig),
 305                            "ineligible_reasons": {a: r for a, r in why.items() if r != "ok"},
 306                            "longs": longs, "shorts": shorts, "signal": sig})
 307          equity0 = cash
 308          open_legs = []
 309          basket_id = len(decisions)
 310          for side, names in ((1, longs), (-1, shorts)):
 311              for a in names:
 312                  e = px.get(a, entry_ts, 0, "entry")
 313                  notional = LEG_FRACTION * equity0
 314                  cost_in = notional * c
 315                  cash -= cost_in
 316                  open_legs.append({"period_variant": variant, "basket": basket_id, "asset": a, "side": side,
 317                                    "entry_ts": entry_ts, "entry": e, "qty": notional / e, "notional": notional,
 318                                    "costs": cost_in, "funding": 0.0, "liquidated": 0, "alive": True, "signal": sig[a],
 319                                    "price_fallbacks": 0,
 320                                    "funding_gaps_in_holding": funding_chain_gaps(market[a], entry_ts, exit_ts - 1) or 0})
 321          t = entry_ts
 322          while t < exit_ts:
 323              for lg in open_legs:
 324                  if not lg["alive"]:
 325                      continue
 326                  a = lg["asset"]
 327                  if t > entry_ts and t in market[a]["funding"]:
 328                      amt = -lg["side"] * market[a]["funding"][t] * lg["qty"] * px.get(a, t, 0, "funding")
 329                      lg["funding"] += amt
 330                  if lg["side"] == -1:
 331                      hi = px.get(a, t, 1, "liquidation_check")
 332                      lg["price_fallbacks"] += px.last_fallback
 333                      if hi >= 2 * lg["entry"]:
 334                          _liquidate(lg, t, 2 * lg["entry"])
 335                          cash += lg["gross"] + lg["funding"]
 336              if (t // HOUR_MS) % 24 == 23:  # close svíčky 23:00 = konec dne
 337                  mtm = sum(lg["side"] * lg["qty"] * (px.get(lg["asset"], t, 3, "mtm") - lg["entry"]) + lg["funding"]
 338                            for lg in open_legs if lg["alive"])
 339                  curve[date_of(t)] = cash + mtm
 340              t += HOUR_MS
 341          for lg in open_legs:
 342              if lg["alive"]:
 343                  x = px.get(lg["asset"], exit_ts, 0, "exit")
 344                  lg["price_fallbacks"] += px.last_fallback
 345                  if lg["side"] == -1 and x >= 2 * lg["entry"]:  # gap přes likvidační cenu ve výstupní hodině
 346                      _liquidate(lg, exit_ts, x)
 347                      cash += lg["gross"] + lg["funding"]
 348                  else:
 349                      cost_out = lg["qty"] * x * c
 350                      lg.update(alive=False, exit_ts=exit_ts, exit=x, gross=lg["side"] * lg["qty"] * (x - lg["entry"]))
 351                      lg["costs"] += cost_out
 352                      cash += lg["gross"] + lg["funding"] - cost_out
 353              lg["net_pnl"] = lg["gross"] + lg["funding"] - lg["costs"]
 354              legs.append(lg)
 355          D += H * DAY_MS
 356      # dny bez otevřeného koše (začátek, přeskočené týdny, konec) = hotovost
 357      # (po konci smyčky jsou všechny nohy uzavřené ⇒ zbylé dny = hotovost)
 358      full, d = {}, start
 359      while d <= end:
 360          full[d] = curve.get(d, START_EQUITY if ms_of(d) < first_decision else cash)
 361          d += timedelta(days=1)
 362      return legs, full, decisions
 363  
 364  
 365  # ------------------------------------------------------------------ metriky
 366  def curve_metrics(curve, start_value):
 367      vals = [curve[d] for d in sorted(curve)]
 368      rets = [vals[0] / start_value - 1] + [vals[k] / vals[k - 1] - 1 for k in range(1, len(vals))]
 369      mu = sum(rets) / len(rets)
 370      sd = math.sqrt(sum((r - mu) ** 2 for r in rets) / (len(rets) - 1)) if len(rets) > 1 else 0.0
 371      peak, mdd = start_value, 0.0
 372      for v in vals:
 373          peak = max(peak, v)
 374          mdd = max(mdd, 1 - v / peak)
 375      return {"return_pct": round((vals[-1] / start_value - 1) * 100, 4),
 376              "sharpe": round(mu / sd * math.sqrt(365), 4) if sd > 0 else 0.0,
 377              "max_drawdown_pct": round(mdd * 100, 4)}, rets
 378  
 379  
 380  def trade_metrics(legs):
 381      pnl = [lg["net_pnl"] for lg in legs]
 382      gains = sum(p for p in pnl if p > 0)
 383      losses = -sum(p for p in pnl if p < 0)
 384      top3 = sum(sorted(pnl, reverse=True)[:3])
 385      return {"trades": len(pnl), "net_pnl": round(sum(pnl), 4),
 386              "profit_factor": round(gains / losses, 4) if losses > 0 else (None if gains == 0 else 999.0),
 387              "net_without_top3": round(sum(pnl) - top3, 4),
 388              "funding": round(sum(lg["funding"] for lg in legs), 4),
 389              "costs": round(sum(lg["costs"] for lg in legs), 4),
 390              "liquidations": sum(lg["liquidated"] for lg in legs),
 391              "long_net": round(sum(lg["net_pnl"] for lg in legs if lg["side"] == 1), 4),
 392              "short_net": round(sum(lg["net_pnl"] for lg in legs if lg["side"] == -1), 4)}
 393  
 394  
 395  def run(market, start, end, mult, W, H, variant, prices=None):
 396      legs, curve, dec = simulate(market, start, end, W, H, mult, variant, prices)
 397      cm, rets = curve_metrics(curve, START_EQUITY)
 398      return {**cm, **trade_metrics(legs), "baskets": sum(1 for x in dec if not x["skipped"]),
 399              "skipped_weeks": sum(1 for x in dec if x["skipped"]),
 400              "edge_funding_events_excluded": simulate_edge_events(market, legs),
 401              "edge_funding_impact_abs_upper_bound": simulate_edge_events(market, legs, True)[1],
 402              "legs_with_price_fallback": sum(1 for lg in legs if lg["price_fallbacks"]),
 403              "legs_with_funding_gap_in_holding": sum(1 for lg in legs if lg["funding_gaps_in_holding"]),
 404              "per_basket": basket_metrics(legs)}, legs, rets, curve
 405  
 406  
 407  def buy_hold(market, start, end, mult, prices=None):
 408      """Oprava R2: B&H 8 perpů (long 12,5 % na aktivum, 1× bez páky, marže = notional) včetně skutečného fundingu:
 409      long platí kladnou sazbu z qty × open svíčky v čase události, pro události v (start 00:00, konec dne end).
 410      Nákup za open první hodiny, prodej za close svíčky 23:00 posledního dne; nedostupné aktivum = hotovost."""
 411      px = prices or Prices(market)
 412      c = (FEE + SLIP) * mult
 413      t0 = ms_of(start)
 414      t_end = ms_of(end) + 23 * HOUR_MS
 415      share = START_EQUITY / len(ASSETS)
 416      qty, cash, funding = {}, 0.0, 0.0
 417      for a in ASSETS:
 418          if t0 in market[a]["bars"]:
 419              qty[a] = share * (1 - c) / px.get(a, t0, 0, "benchmark")
 420          else:
 421              cash += share
 422      events = sorted((t, a) for a in qty for t in market[a]["fts"] if t0 < t <= t_end)
 423      k, curve, d = 0, {}, start
 424      while d <= end:
 425          t = ms_of(d) + 23 * HOUR_MS
 426          while k < len(events) and events[k][0] <= t:
 427              te, a = events[k]
 428              funding -= market[a]["funding"][te] * qty[a] * px.get(a, te, 0, "benchmark")
 429              k += 1
 430          curve[d] = cash + funding + sum(q * px.get(a, t, 3, "benchmark") for a, q in qty.items())
 431          d += timedelta(days=1)
 432      asset_value = curve[end] - cash - funding
 433      curve[end] = cash + funding + asset_value * (1 - c)
 434      cm, rets = curve_metrics(curve, START_EQUITY)
 435      return {**cm, "net_pnl": round(curve[end] - START_EQUITY, 4), "funding": round(funding, 4)}, rets
 436  
 437  
 438  def simulate_edge_events(market, legs, with_impact=False):
 439      """Funding události přesně v čase vstupu/výstupu nohy — podle protokolu se nezapočítají (dodatek 1).
 440      with_impact: (počet, součet |sazba × qty × cena|) = horní mez dopadu na P/L (dodatek 2, E)."""
 441      n, impact = 0, 0.0
 442      for lg in legs:
 443          m = market[lg["asset"]]
 444          for t, p in ((lg["entry_ts"], lg["entry"]), (lg["exit_ts"], lg["exit"])):
 445              if t in m["funding"]:
 446                  n += 1
 447                  impact += abs(m["funding"][t] * lg["qty"] * p)
 448      return (n, round(impact, 6)) if with_impact else n
 449  
 450  
 451  def basket_metrics(legs):
 452      """Dodatek 2 (B): metriky z celých košů (4 nohy jednoho rozhodnutí nejsou 4 nezávislá rozhodnutí)."""
 453      by = {}
 454      for lg in legs:
 455          by.setdefault(lg["basket"], []).append(lg)
 456      pnl = [sum(x["net_pnl"] for x in b) for _, b in sorted(by.items())]
 457      gains = sum(x for x in pnl if x > 0)
 458      losses = -sum(x for x in pnl if x < 0)
 459      return {"baskets": len(pnl), "net_pnl": round(sum(pnl), 4),
 460              "profit_factor": round(gains / losses, 4) if losses > 0 else (None if gains == 0 else 999.0),
 461              "net_without_top3": round(sum(pnl) - sum(sorted(pnl, reverse=True)[:3]), 4),
 462              "baskets_with_price_fallback": sum(1 for _, b in by.items() if any(x["price_fallbacks"] for x in b)),
 463              "baskets_with_funding_gap": sum(1 for _, b in by.items() if any(x["funding_gaps_in_holding"] for x in b))}
 464  
 465  
 466  def vol_matched(strategy_rets, bh_rets):
 467      """Info (dodatek 1): B&H přeškálované na stejnou denní volatilitu jako strategie (bez nákladů); kritéria nemění.
 468      EX-POST diagnostika (škála z celého období), ne obchodovatelný benchmark (dodatek 2, F)."""
 469      def sd(x):
 470          if len(x) < 2:
 471              return 0.0
 472          mu = sum(x) / len(x)
 473          return math.sqrt(sum((r - mu) ** 2 for r in x) / (len(x) - 1))
 474      k = sd(strategy_rets) / sd(bh_rets) if sd(bh_rets) > 0 else 0.0
 475      v, peak, mdd = 1.0, 1.0, 0.0
 476      for r in bh_rets:
 477          v *= 1 + k * r
 478          peak = max(peak, v)
 479          mdd = max(mdd, 1 - v / peak)
 480      return {"kind": "ex_post_diagnostic", "scale": round(k, 6), "return_pct": round((v - 1) * 100, 4), "max_drawdown_pct": round(mdd * 100, 4)}
 481  
 482  
 483  def corr(x, y):
 484      n = min(len(x), len(y))
 485      x, y = x[:n], y[:n]
 486      mx, my = sum(x) / n, sum(y) / n
 487      sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
 488      sx = math.sqrt(sum((a - mx) ** 2 for a in x))
 489      sy = math.sqrt(sum((b - my) ** 2 for b in y))
 490      return round(sxy / (sx * sy), 4) if sx > 0 and sy > 0 else None
 491  
 492  
 493  def btc_daily_returns(market, start, end, prices):
 494      vals, d = [], start - timedelta(days=1)
 495      while d <= end:
 496          vals.append(prices.get("BTCUSDT", ms_of(d) + 23 * HOUR_MS, 3, "benchmark"))
 497          d += timedelta(days=1)
 498      return [vals[k] / vals[k - 1] - 1 for k in range(1, len(vals))]
 499  
 500  
 501  def evaluate(res, bh):
 502      v1, v2 = res["validation"]["x1"], res["validation"]["x2"]
 503      f2, t1 = res["final_test"]["x2"], res["tuning"]["x1"]
 504      bv, bf = bh["validation"]["x1"], bh["final_test"]["x2"]
 505      a = {"A1_sharpe_dd": v1["sharpe"] > bv["sharpe"] and v1["max_drawdown_pct"] < bv["max_drawdown_pct"],
 506           "A2_trades_ge_30": v1["trades"] >= 30,
 507           "A3_x2_pf_profit": (v2["profit_factor"] or 0) > 1.2 and v2["net_pnl"] > 0,
 508           "A4_wo_top3": v1["net_without_top3"] > 0,
 509           "A5_final_x2": f2["net_pnl"] > 0 and f2["sharpe"] > bf["sharpe"]
 510           and f2["max_drawdown_pct"] < bf["max_drawdown_pct"]}
 511      b = {"B1_val_x2_profit_pf": v2["net_pnl"] > 0 and (v2["profit_factor"] or 0) > 1.2,
 512           "B2_dd_le_0_6_bh": v1["max_drawdown_pct"] <= 0.6 * bv["max_drawdown_pct"]
 513           and res["final_test"]["x1"]["max_drawdown_pct"] <= 0.6 * bh["final_test"]["x1"]["max_drawdown_pct"],
 514           "B3_final_x2_profit": f2["net_pnl"] > 0,
 515           "B4_val_wo_top3": v1["net_without_top3"] > 0,
 516           "B5_trades_ge_20": v1["trades"] + res["final_test"]["x1"]["trades"] >= 20,
 517           "B6_tuning_x1_profit": t1["net_pnl"] > 0}
 518      return a, b
 519  
 520  
 521  def safe_dsr(rets, n, var_annual):
 522      """Oprava R4: nedefinované DSR (nulový rozptyl, např. žádné obchody) = None + důvod, brána neprošla."""
 523      sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
 524      from tools.research.deflated_sharpe import dsr_from_returns
 525      try:
 526          return {**dsr_from_returns(rets, n, var_annual / 365), "undefined_reason": None}
 527      except (ValueError, ZeroDivisionError) as e:
 528          return {"dsr": None, "undefined_reason": str(e), "n_trials": n, "var_trials": var_annual / 365}
 529  
 530  
 531  DSR_SENSITIVITY_N = (159, 318, 636)
 532  DSR_SENSITIVITY_V = (0.5, 1.0, 2.0)
 533  
 534  
 535  def neighbors(w, h):
 536      return [(w2, h2) for (w2, h2) in GRID if (w2 == w) != (h2 == h)]
 537  
 538  
 539  def pdate(s):
 540      return date.fromisoformat(s)
 541  
 542  
 543  def leg_row(period, mult, lg):
 544      return {"period": period, "variant": lg["period_variant"], "cost_mult": mult, "asset": lg["asset"],
 545              "side": "LONG" if lg["side"] == 1 else "SHORT", "signal_funding_sum": round(lg["signal"], 8),
 546              "entry_utc": datetime.fromtimestamp(lg["entry_ts"] / 1000, tz=timezone.utc).isoformat(),
 547              "exit_utc": datetime.fromtimestamp(lg["exit_ts"] / 1000, tz=timezone.utc).isoformat(),
 548              "entry": lg["entry"], "exit": lg["exit"], "qty": round(lg["qty"], 10),
 549              "notional": round(lg["notional"], 6), "gross": round(lg["gross"], 6),
 550              "funding": round(lg["funding"], 6), "costs": round(lg["costs"], 6),
 551              "liquidated": lg["liquidated"], "basket": lg["basket"], "price_fallbacks": lg["price_fallbacks"],
 552              "funding_gaps_in_holding": lg["funding_gaps_in_holding"], "net_pnl": round(lg["net_pnl"], 6)}
 553  
 554  
 555  def main(argv=None):
 556      ap = argparse.ArgumentParser()
 557      ap.add_argument("--cache", default="/tmp/vision-fd")
 558      ap.add_argument("--outdir", default="research/funding_dispersion")
 559      args = ap.parse_args(argv)
 560      out = Path(args.outdir)
 561      market, manifest, missing, fatal = load(args.cache)
 562      (out / "data_source.json").write_text(json.dumps({"archives": manifest, "missing": missing}, indent=1))
 563      if fatal:
 564          print("FATAL missing archives after first available month", json.dumps(fatal[:30]))
 565          sys.exit(2)
 566      first_bar = {a: date_of(market[a]["first_bar"]).isoformat() if market[a]["first_bar"] else None for a in ASSETS}
 567      first_funding = {a: date_of(market[a]["first_funding"]).isoformat() if market[a]["first_funding"] else None
 568                       for a in ASSETS}
 569      print("DATA_COVERAGE", json.dumps({"first_bar": first_bar, "first_funding": first_funding}))
 570      px = Prices(market)
 571  
 572      rows, results, tune, rets_store = [], {}, {}, {}
 573      for (w, h) in GRID:
 574          tag = vt(w, h)
 575          results[tag] = {}
 576          for p, (s, e) in PERIODS.items():
 577              results[tag][p] = {}
 578              for m in COST_MULTIPLIERS:
 579                  r, legs, rets, _ = run(market, pdate(s), pdate(e), m, w, h, tag, px)
 580                  results[tag][p][f"x{m}"] = r
 581                  rets_store[(tag, p, m)] = rets
 582                  rows += [leg_row(p, m, lg) for lg in legs]
 583          tune[tag] = results[tag]["tuning"]["x1"]
 584      chosen = max(GRID, key=lambda g: (tune[vt(*g)]["net_pnl"], -GRID.index(g)))
 585      ctag = vt(*chosen)
 586      bh, bh_rets = {}, {}
 587      for p, (s, e) in PERIODS.items():
 588          bh[p] = {}
 589          for m in COST_MULTIPLIERS:
 590              bh[p][f"x{m}"], bh_rets[(p, m)] = buy_hold(market, pdate(s), pdate(e), m, px)
 591      wf = {}
 592      for y in WF_YEARS:
 593          r, legs, _, _ = run(market, date(y, 1, 1), date(y, 12, 31), 2, chosen[0], chosen[1], ctag, px)
 594          wf[str(y)] = r
 595          rows += [leg_row(f"wf_{y}", 2, lg) for lg in legs]
 596  
 597      res = results[ctag]
 598      track_a, track_b = evaluate(res, bh)
 599      passed_a, passed_b = all(track_a.values()), all(track_b.values())
 600      vrets = rets_store[(ctag, "validation", 1)]
 601      dsr = safe_dsr(vrets, DSR_N, DSR_VAR_ANNUAL)
 602      dsr_sens = {f"N{n}_V{v}": safe_dsr(vrets, n, v)["dsr"] for n in DSR_SENSITIVITY_N for v in DSR_SENSITIVITY_V}
 603      nb = {vt(*g): results[vt(*g)]["validation"]["x2"]["net_pnl"] for g in neighbors(*chosen)}
 604      wf_pos = sum(1 for y in wf.values() if y["net_pnl"] > 0)
 605      robust = {"dsr_ge_0_95": dsr["dsr"] is not None and dsr["dsr"] >= 0.95,
 606                "neighbors_val_x2_profit": all(v > 0 for v in nb.values()),
 607                "walk_forward_ge_3_of_4": wf_pos >= 3}
 608      s, e = PERIODS["validation"]
 609      beta_info = {"corr_daily_vs_btc_validation_x1": corr(rets_store[(ctag, "validation", 1)],
 610                                                           btc_daily_returns(market, pdate(s), pdate(e), px)),
 611                   "gross_exposure_strategy": 4 * LEG_FRACTION, "gross_exposure_bh": 1.0,
 612                   "bh_vol_matched_x1": {p: vol_matched(rets_store[(ctag, p, 1)], bh_rets[(p, 1)])
 613                                         for p in ("validation", "final_test")}}
 614      verdict = ("KANDIDÁT NA FORWARD PAPER" if (passed_a or passed_b) and all(robust.values()) else "ZAMÍTNUTO")
 615      flags = {"edge_funding_events": sum(res[p]["x1"]["edge_funding_events_excluded"] for p in PERIODS),
 616               "legs_with_price_fallback": sum(res[p]["x1"]["legs_with_price_fallback"] for p in PERIODS),
 617               "legs_with_funding_gap_in_holding": sum(res[p]["x1"]["legs_with_funding_gap_in_holding"] for p in PERIODS)}
 618      if verdict.startswith("KANDIDÁT") and any(flags.values()):
 619          verdict = "NEROZHODNUTO — výsledek ovlivněn hranami fundingu / mezerami dat, nutná revize (dodatek 2)"
 620      payload = {"protocol": "research/funding_dispersion/PROTOCOL.md", "chosen": ctag,
 621                 "tuning_selection_x1": tune, "strategy": results, "buy_hold_equal_8": bh,
 622                 "walk_forward_x2": wf,
 623                 "walk_forward_note": "roční stabilita fixní varianty vybrané na 2020-10…2022; pro 2021–22 NE čistý OOS walk-forward", "neighbors_val_x2": nb, "track_a": track_a, "track_b": track_b,
 624                 "passed_a": passed_a, "passed_b": passed_b, "dsr_validation_x1": dsr,
 625                 "dsr_note": "N = 159 je pracovní odhad (ne doložená horní mez); V[SR] = 0,5 p.a. je předpoklad",
 626                 "dsr_sensitivity_scenarios": dsr_sens, "robustness": robust, "interpretation_flags": flags,
 627                 "info": {**beta_info, "price_fallbacks_by_purpose": px.fallbacks, "first_bar": first_bar,
 628                          "first_funding": first_funding,
 629                          "load_audit": {a: market[a].get("load_audit") for a in ASSETS}},
 630                 "verdict": verdict}
 631      (out / "results.json").write_text(json.dumps(payload, indent=1, default=str))
 632      with open(out / "trades.csv", "w", newline="") as fh:
 633          w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["period"])
 634          w.writeheader()
 635          w.writerows(rows)
 636      print("SUMMARY", json.dumps({"chosen": ctag, "verdict": verdict, "track_a": track_a, "track_b": track_b,
 637                                   "robust": robust, "dsr": dsr["dsr"], "dsr_sens": dsr_sens, "flags": flags,
 638                                   "neighbors": nb,
 639                                   "val": res["validation"], "final": res["final_test"], "tuning": res["tuning"],
 640                                   "bh_val": bh["validation"]["x1"], "bh_final": bh["final_test"]["x2"],
 641                                   "wf": {k: v["net_pnl"] for k, v in wf.items()}, **beta_info,
 642                                   "fallbacks": px.fallbacks}, default=str))
 643  
 644  
 645  if __name__ == "__main__":
 646      main()
````

## C2. tests/test_funding_dispersion.py (`b5999e6`)
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
````

## D1. research/spot_led/PROTOCOL.md (`e77f2f9`)
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
````

## D2. research/spot_led/run.py (`e77f2f9`)
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
  86      return [(normalize_funding_ts(_ms(int(r[0]))), float(r[2])) for r in _csv_rows(payload)]
  87  
  88  
  89  def urls(asset):
  90      b = "https://data.binance.vision/data"
  91      for y, m in months():
  92          tag = f"{y}-{m:02d}"
  93          yield "spot", (y, m), f"{b}/spot/monthly/klines/{asset}/5m/{asset}-5m-{tag}.zip"
  94          yield "perp", (y, m), f"{b}/futures/um/monthly/klines/{asset}/5m/{asset}-5m-{tag}.zip"
  95          yield "fr", (y, m), f"{b}/futures/um/monthly/fundingRate/{asset}/{asset}-fundingRate-{tag}.zip"
  96  
  97  
  98  def load(cache, fetcher=fetch):
  99      market, manifest, missing, fatal = {}, [], [], []
 100      parsers = {"spot": parse_spot, "perp": parse_perp, "fr": parse_funding}
 101      for a in ASSETS:
 102          raw = {"spot": {}, "perp": {}, "fr": {}}
 103          present, miss = {k: [] for k in raw}, {k: [] for k in raw}
 104          for kind, ym, url in urls(a):
 105              p = Path(cache) / kind / url.rsplit("/", 1)[1]
 106              if not p.exists():
 107                  try:
 108                      payload = fetcher(url)
 109                  except urllib.error.HTTPError as e:
 110                      missing.append({"url": url, "http": e.code})
 111                      miss[kind].append(ym)
 112                      continue
 113                  p.parent.mkdir(parents=True, exist_ok=True)
 114                  p.write_bytes(payload)
 115              payload = p.read_bytes()
 116              present[kind].append(ym)
 117              rows = parsers[kind](payload)
 118              for r in rows:
 119                  raw[kind][r[0]] = r[1:] if kind != "fr" else r[1]
 120              manifest.append({"url": url, "sha256": hashlib.sha256(payload).hexdigest(), "rows": len(rows)})
 121          for kind in raw:
 122              if present[kind]:
 123                  first = min(present[kind])
 124                  fatal += [{"asset": a, "kind": kind, "month": f"{y}-{m:02d}"} for (y, m) in miss[kind] if (y, m) > first]
 125              else:
 126                  fatal.append({"asset": a, "kind": kind, "month": "all"})
 127          market[a] = prepare(raw["spot"], raw["perp"], raw["fr"])
 128      return market, manifest, missing, fatal
 129  
 130  
 131  def prepare(spot, perp, fund):
 132      """spot {ts: (close, vol, taker_buy)}, perp {ts: (open, close)}, fund {ts: rate}."""
 133      perp_ts = sorted(perp)
 134      return {"spot": spot, "perp": perp, "perp_ts": perp_ts, "funding": dict(sorted(fund.items())),
 135              "features": features(spot, perp)}
 136  
 137  
 138  def features(spot, perp):
 139      """Pro každý spot čas T se svíčkami T a T−5m v obou trzích: (T, podíl, r_spot, r_perp). Jen data ≤ T."""
 140      out = []
 141      for T in sorted(spot):
 142          s, sp = spot[T], spot.get(T - BAR)
 143          p, pp = perp.get(T), perp.get(T - BAR)
 144          if sp is None or p is None or pp is None or s[1] <= 0 or sp[0] <= 0 or pp[1] <= 0:
 145              continue
 146          out.append((T, s[2] / s[1], s[0] / sp[0] - 1, p[1] / pp[1] - 1))
 147      return out
 148  
 149  
 150  def gap_audit(m):
 151      spot, perp = m["spot"], m["perp"]
 152      def missing(ts_sorted):
 153          return sum(max(0, (b - a) // BAR - 1) for a, b in zip(ts_sorted, ts_sorted[1:]))
 154      ss = set(spot)
 155      ps = set(perp)
 156      return {"spot_bars": len(spot), "perp_bars": len(perp), "spot_missing_5m": missing(sorted(spot)),
 157              "perp_missing_5m": missing(m["perp_ts"]), "spot_only": len(ss - ps), "perp_only": len(ps - ss),
 158              "usable_signal_bars": len(m["features"])}
 159  
 160  
 161  # ------------------------------------------------------------------ simulace
 162  def ms_of(d):
 163      return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)
 164  
 165  
 166  def date_of(ms):
 167      return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date()
 168  
 169  
 170  def perp_price_at(m, t):
 171      """open svíčky v t; chybí-li, close poslední dřívější svíčky."""
 172      b = m["perp"].get(t)
 173      if b is not None:
 174          return b[0]
 175      i = bisect.bisect_left(m["perp_ts"], t) - 1
 176      if i < 0:
 177          raise KeyError(t)
 178      return m["perp"][m["perp_ts"][i]][1]
 179  
 180  
 181  MAX_EXIT_DELAY_MS = 60 * 60_000  # dodatek 1: výstup se smí kvůli mezeře zpozdit nejvýš o 60 min
 182  
 183  
 184  def candidates(m, asset, start_ms, end_ms, th, hold, delay_bars=0):
 185      """Kandidátní obchody jednoho aktiva (nezávislé na equity): bez překryvu, výstup uvnitř období.
 186      delay_bars: informativní citlivost na latenci (vstup o N svíček později), výběr varianty neovlivňuje.
 187      Okraj období se posuzuje jen podle času (plánovaný výstup + max. zpoždění < konec), ne podle existence dat."""
 188      hold_ms = hold * 60_000
 189      out, free_from = [], -1
 190      feats = m["features"]
 191      i = bisect.bisect_left(feats, (start_ms - BAR,))  # vstup (T+5m) ≥ start
 192      for T, share, rs, rp in feats[i:]:
 193          entry_t = T + BAR * (1 + delay_bars)
 194          if entry_t >= end_ms:
 195              break
 196          if entry_t < start_ms or T + BAR < free_from:
 197              continue
 198          if share > th and rs > R_SPOT and rp < R_PERP:
 199              side = 1
 200          elif share < 1 - th and rs < -R_SPOT and rp > -R_PERP:
 201              side = -1
 202          else:
 203              continue
 204          planned = entry_t + hold_ms
 205          if planned + MAX_EXIT_DELAY_MS >= end_ms:
 206              continue
 207          if entry_t not in m["perp"]:
 208              continue
 209          j = bisect.bisect_left(m["perp_ts"], planned)
 210          if j < len(m["perp_ts"]) and m["perp_ts"][j] <= planned + MAX_EXIT_DELAY_MS:
 211              exit_t = m["perp_ts"][j]
 212              exit_px = m["perp"][exit_t][0]
 213              gap = int(exit_t != planned)
 214          else:  # mezera delší než limit ⇒ DATA_GAP: poslední pozorovaný close před plánovaným výstupem (nerealizovatelné)
 215              k = bisect.bisect_left(m["perp_ts"], planned) - 1
 216              exit_t = planned + MAX_EXIT_DELAY_MS
 217              exit_px = m["perp"][m["perp_ts"][k]][1]
 218              gap = 2
 219          # funding: události s entry_t < t < exit_t (seznam pro denní ocenění přes půlnoc)
 220          f_events = []
 221          t = (entry_t // HOUR_MS + 1) * HOUR_MS
 222          while t < exit_t:
 223              if t in m["funding"]:
 224                  f_events.append((t, -side * m["funding"][t] * perp_price_at(m, t)))
 225              t += HOUR_MS
 226          out.append({"asset": asset, "side": side, "signal_ts": T, "entry_ts": entry_t, "exit_ts": exit_t,
 227                      "entry": m["perp"][entry_t][0], "exit": exit_px, "funding_unit": sum(x for _, x in f_events),
 228                      "funding_events": f_events, "share": share, "r_spot": rs, "r_perp": rp, "data_gap": gap})
 229          free_from = exit_t
 230      return out
 231  
 232  
 233  def close_before(m, t):
 234      """close poslední perp svíčky uzavřené nejpozději v t (svíčka s open ≤ t − 5 min)."""
 235      i = bisect.bisect_right(m["perp_ts"], t - BAR) - 1
 236      return m["perp"][m["perp_ts"][i]][1] if i >= 0 else None
 237  
 238  
 239  def simulate(market, start, end, th, hold, mult, variant="", delay_bars=0):
 240      """Sdílená equity: notional = 10 % realizované equity při vstupu. Vrací (obchody, denní equity).
 241      Denní equity = realizované obchody + ocenění pozic otevřených přes půlnoc (close poslední svíčky dne,
 242      vstupní náklady, funding do půlnoci) — oprava podle oponentury (bod G)."""
 243      c = (FEE + SLIP) * mult
 244      s_ms, e_ms = ms_of(start), ms_of(end) + DAY_MS
 245      cands = sorted((x for a in ASSETS for x in candidates(market[a], a, s_ms, e_ms, th, hold, delay_bars)),
 246                     key=lambda x: (x["entry_ts"], x["asset"]))
 247      cash, pending, trades = START_EQUITY, [], []
 248      for x in cands:
 249          while pending and pending[0][0] <= x["entry_ts"]:
 250              _, _, tr = heapq.heappop(pending)
 251              cash += tr["net_pnl"]
 252          notional = FRACTION * cash
 253          qty = notional / x["entry"]
 254          gross = x["side"] * qty * (x["exit"] - x["entry"])
 255          costs = notional * c + qty * x["exit"] * c
 256          fund = qty * x["funding_unit"]
 257          tr = {**x, "variant": variant, "cost_mult": mult, "qty": qty, "notional": notional, "gross": gross,
 258                "funding": fund, "costs": costs, "net_pnl": gross + fund - costs, "cost_in": notional * c,
 259                "gross_bp": x["side"] * (x["exit"] / x["entry"] - 1) * 1e4}
 260          trades.append(tr)
 261          heapq.heappush(pending, (x["exit_ts"], len(trades), tr))
 262      realized_by_day, overnight = {}, {}
 263      for tr in trades:
 264          d = date_of(tr["exit_ts"] - 1)  # výstup přesně v 00:00 patří do dne, který právě skončil
 265          realized_by_day[d] = realized_by_day.get(d, 0.0) + tr["net_pnl"]
 266          day_end = (tr["entry_ts"] // DAY_MS + 1) * DAY_MS
 267          while day_end < tr["exit_ts"]:  # otevřeno přes půlnoc
 268              p = close_before(market[tr["asset"]], day_end)
 269              mtm = tr["side"] * tr["qty"] * (p - tr["entry"]) - tr["cost_in"] + \
 270                  tr["qty"] * sum(v for t, v in tr["funding_events"] if t <= day_end)
 271              dd = date_of(day_end - 1)
 272              overnight[dd] = overnight.get(dd, 0.0) + mtm
 273              day_end += DAY_MS
 274      curve, eq, d = {}, START_EQUITY, start
 275      while d <= end:
 276          eq += realized_by_day.get(d, 0.0)
 277          curve[d] = eq + overnight.get(d, 0.0)
 278          d += timedelta(days=1)
 279      return trades, curve
 280  
 281  
 282  # ------------------------------------------------------------------ metriky
 283  def curve_metrics(curve, start_value):
 284      vals = [curve[d] for d in sorted(curve)]
 285      rets = [vals[0] / start_value - 1] + [vals[k] / vals[k - 1] - 1 for k in range(1, len(vals))]
 286      mu = sum(rets) / len(rets)
 287      sd = math.sqrt(sum((r - mu) ** 2 for r in rets) / (len(rets) - 1)) if len(rets) > 1 else 0.0
 288      peak, mdd = start_value, 0.0
 289      for v in vals:
 290          peak = max(peak, v)
 291          mdd = max(mdd, 1 - v / peak)
 292      return {"return_pct": round((vals[-1] / start_value - 1) * 100, 4),
 293              "sharpe": round(mu / sd * math.sqrt(365), 4) if sd > 0 else 0.0,
 294              "max_drawdown_pct": round(mdd * 100, 4)}, rets
 295  
 296  
 297  def trade_metrics(trades, start, end):
 298      pnl = [t["net_pnl"] for t in trades]
 299      gains = sum(p for p in pnl if p > 0)
 300      losses = -sum(p for p in pnl if p < 0)
 301      top3 = sum(sorted(pnl, reverse=True)[:3])
 302      years = max((end - start).days + 1, 1) / 365.25
 303      return {"trades": len(pnl), "net_pnl": round(sum(pnl), 4),
 304              "profit_factor": round(gains / losses, 4) if losses > 0 else (None if gains == 0 else 999.0),
 305              "net_without_top3": round(sum(pnl) - top3, 4),
 306              "funding": round(sum(t["funding"] for t in trades), 4),
 307              "costs": round(sum(t["costs"] for t in trades), 4),
 308              "long_trades": sum(1 for t in trades if t["side"] == 1),
 309              "short_trades": sum(1 for t in trades if t["side"] == -1),
 310              "data_gap_exits": sum(1 for t in trades if t["data_gap"]),
 311              "data_gap_unrealizable_exits": sum(1 for t in trades if t["data_gap"] == 2),
 312              "avg_gross_bp": round(sum(t["gross_bp"] for t in trades) / len(trades), 3) if trades else None,
 313              "trades_per_year_per_asset": {a: round(sum(1 for t in trades if t["asset"] == a) / years, 1)
 314                                            for a in ASSETS}}
 315  
 316  
 317  def run(market, start, end, mult, th, hold, variant, delay_bars=0):
 318      trades, curve = simulate(market, start, end, th, hold, mult, variant, delay_bars)
 319      cm, rets = curve_metrics(curve, START_EQUITY)
 320      return {**cm, **trade_metrics(trades, start, end)}, trades, rets
 321  
 322  
 323  def day_close(m, d):
 324      t = ms_of(d) + DAY_MS
 325      i = bisect.bisect_left(m["perp_ts"], t) - 1
 326      return m["perp"][m["perp_ts"][i]][1]
 327  
 328  
 329  def buy_hold(market, start, end, mult):
 330      """B&H 3 perpů stejnými vahami, 1× bez páky, včetně skutečného fundingu (long platí kladnou sazbu)."""
 331      c = (FEE + SLIP) * mult
 332      t0 = ms_of(start)
 333      t_end = ms_of(end) + DAY_MS
 334      qty = {}
 335      for a in ASSETS:
 336          m = market[a]
 337          j = bisect.bisect_left(m["perp_ts"], t0)
 338          qty[a] = START_EQUITY / len(ASSETS) * (1 - c) / m["perp"][m["perp_ts"][j]][0]
 339      events = sorted((t, a) for a in ASSETS for t in market[a]["funding"] if t0 < t < t_end)
 340      k, funding, curve, d = 0, 0.0, {}, start
 341      while d <= end:
 342          t_day = ms_of(d) + DAY_MS
 343          while k < len(events) and events[k][0] < t_day:
 344              te, a = events[k]
 345              funding -= market[a]["funding"][te] * qty[a] * perp_price_at(market[a], te)
 346              k += 1
 347          curve[d] = funding + sum(q * day_close(market[a], d) for a, q in qty.items())
 348          d += timedelta(days=1)
 349      curve[end] = funding + (curve[end] - funding) * (1 - c)
 350      cm, _ = curve_metrics(curve, START_EQUITY)
 351      return {**cm, "net_pnl": round(curve[end] - START_EQUITY, 4), "funding": round(funding, 4)}
 352  
 353  
 354  def safe_dsr(rets, n, var_annual):
 355      """Nedefinované DSR (nulový rozptyl, např. 0 obchodů) = None + důvod; brána pak neprošla."""
 356      sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
 357      from tools.research.deflated_sharpe import dsr_from_returns
 358      try:
 359          return {**dsr_from_returns(rets, n, var_annual / 365), "undefined_reason": None}
 360      except (ValueError, ZeroDivisionError) as e:
 361          return {"dsr": None, "undefined_reason": str(e), "n_trials": n, "var_trials": var_annual / 365}
 362  
 363  
 364  def evaluate(res, bh):
 365      v1, v2 = res["validation"]["x1"], res["validation"]["x2"]
 366      f2, t1 = res["final_test"]["x2"], res["tuning"]["x1"]
 367      bv, bf = bh["validation"]["x1"], bh["final_test"]["x2"]
 368      a = {"A1_sharpe_dd": v1["sharpe"] > bv["sharpe"] and v1["max_drawdown_pct"] < bv["max_drawdown_pct"],
 369           "A2_trades_ge_30": v1["trades"] >= 30,
 370           "A3_x2_pf_profit": (v2["profit_factor"] or 0) > 1.2 and v2["net_pnl"] > 0,
 371           "A4_wo_top3": v1["net_without_top3"] > 0,
 372           "A5_final_x2": f2["net_pnl"] > 0 and f2["sharpe"] > bf["sharpe"]
 373           and f2["max_drawdown_pct"] < bf["max_drawdown_pct"]}
 374      b = {"B1_val_x2_profit_pf": v2["net_pnl"] > 0 and (v2["profit_factor"] or 0) > 1.2,
 375           "B2_dd_le_0_6_bh": v1["max_drawdown_pct"] <= 0.6 * bv["max_drawdown_pct"]
 376           and res["final_test"]["x1"]["max_drawdown_pct"] <= 0.6 * bh["final_test"]["x1"]["max_drawdown_pct"],
 377           "B3_final_x2_profit": f2["net_pnl"] > 0,
 378           "B4_val_wo_top3": v1["net_without_top3"] > 0,
 379           "B5_trades_ge_20": v1["trades"] + res["final_test"]["x1"]["trades"] >= 20,
 380           "B6_tuning_x1_profit": t1["net_pnl"] > 0}
 381      return a, b
 382  
 383  
 384  def neighbors(th, hold):
 385      return [(t2, h2) for (t2, h2) in GRID if (t2 == th) != (h2 == hold)]
 386  
 387  
 388  def pdate(s):
 389      return date.fromisoformat(s)
 390  
 391  
 392  def iso(ms):
 393      return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()
 394  
 395  
 396  def trade_row(period, t):
 397      return {"period": period, "variant": t["variant"], "cost_mult": t["cost_mult"], "asset": t["asset"],
 398              "side": "LONG" if t["side"] == 1 else "SHORT", "signal_bar_utc": iso(t["signal_ts"]),
 399              "entry_utc": iso(t["entry_ts"]), "exit_utc": iso(t["exit_ts"]), "entry": t["entry"], "exit": t["exit"],
 400              "taker_buy_share": round(t["share"], 6), "r_spot": round(t["r_spot"], 6), "r_perp": round(t["r_perp"], 6),
 401              "qty": round(t["qty"], 10), "notional": round(t["notional"], 6), "gross": round(t["gross"], 6),
 402              "funding": round(t["funding"], 6), "costs": round(t["costs"], 6), "data_gap": t["data_gap"],
 403              "net_pnl": round(t["net_pnl"], 6)}
 404  
 405  
 406  def main(argv=None):
 407      ap = argparse.ArgumentParser()
 408      ap.add_argument("--cache", default="/tmp/vision-5m")
 409      ap.add_argument("--outdir", default="research/spot_led")
 410      args = ap.parse_args(argv)
 411      out = Path(args.outdir)
 412      market, manifest, missing, fatal = load(args.cache)
 413      (out / "data_source.json").write_text(json.dumps({"archives": manifest, "missing": missing}, indent=1))
 414      if fatal:
 415          print("FATAL missing archives after first available month", json.dumps(fatal[:30]))
 416          sys.exit(2)
 417      audit = {a: gap_audit(market[a]) for a in ASSETS}
 418      print("GAP_AUDIT", json.dumps(audit))
 419  
 420      rows, results, tune, rets_store = [], {}, {}, {}
 421      for (th, hold) in GRID:
 422          tag = vt(th, hold)
 423          results[tag] = {}
 424          for p, (s, e) in PERIODS.items():
 425              results[tag][p] = {}
 426              for m in COST_MULTIPLIERS:
 427                  r, trades, rets = run(market, pdate(s), pdate(e), m, th, hold, tag)
 428                  results[tag][p][f"x{m}"] = r
 429                  rets_store[(tag, p, m)] = rets
 430                  rows += [trade_row(p, t) for t in trades]
 431          tune[tag] = results[tag]["tuning"]["x1"]
 432      chosen = max(GRID, key=lambda g: (tune[vt(*g)]["net_pnl"], -GRID.index(g)))
 433      ctag = vt(*chosen)
 434      bh = {p: {f"x{m}": buy_hold(market, pdate(s), pdate(e), m) for m in COST_MULTIPLIERS}
 435            for p, (s, e) in PERIODS.items()}
 436      wf = {}
 437      for y in WF_YEARS:
 438          r, trades, _ = run(market, date(y, 1, 1), date(y, 12, 31), 2, chosen[0], chosen[1], ctag)
 439          wf[str(y)] = r
 440          rows += [trade_row(f"wf_{y}", t) for t in trades]
 441  
 442      res = results[ctag]
 443      track_a, track_b = evaluate(res, bh)
 444      passed_a, passed_b = all(track_a.values()), all(track_b.values())
 445      vrets = rets_store[(ctag, "validation", 1)]
 446      dsr = safe_dsr(vrets, DSR_N, DSR_VAR_ANNUAL)
 447      dsr_sens = {f"N{n}_V{v}": safe_dsr(vrets, n, v)["dsr"] for n in (159, 318, 636) for v in (0.5, 1.0, 2.0)}
 448      latency = {p: {f"x{m}": run(market, pdate(PERIODS[p][0]), pdate(PERIODS[p][1]), m, chosen[0], chosen[1],
 449                                  ctag + "_lat5m", delay_bars=1)[0] for m in (1, 2)} for p in ("validation", "final_test")}
 450      nb = {vt(*g): results[vt(*g)]["validation"]["x2"]["net_pnl"] for g in neighbors(*chosen)}
 451      wf_pos = sum(1 for y in wf.values() if y["net_pnl"] > 0)
 452      robust = {"dsr_ge_0_95": dsr["dsr"] is not None and dsr["dsr"] >= 0.95, "neighbors_val_x2_profit": all(v > 0 for v in nb.values()),
 453                "walk_forward_ge_3_of_4": wf_pos >= 3}
 454      verdict = ("KANDIDÁT NA FORWARD PAPER" if (passed_a or passed_b) and all(robust.values()) else "ZAMÍTNUTO")
 455      gap_flags = sum(res[p]["x1"]["data_gap_unrealizable_exits"] for p in PERIODS)
 456      if verdict.startswith("KANDIDÁT") and (gap_flags or latency["validation"]["x2"]["net_pnl"] <= 0):
 457          verdict = "NEROZHODNUTO — nerealizovatelné výstupy kvůli mezerám nebo ztráta při latenci +5 min, nutná revize"
 458      payload = {"protocol": "research/spot_led/PROTOCOL.md", "chosen": ctag, "tuning_selection_x1": tune,
 459                 "strategy": results, "buy_hold_equal_3": bh, "walk_forward_x2": wf, "neighbors_val_x2": nb,
 460                 "track_a": track_a, "track_b": track_b, "passed_a": passed_a, "passed_b": passed_b,
 461                 "dsr_validation_x1": dsr,
 462                 "dsr_note": "N = 159 je pracovní odhad (ne doložená horní mez); V[SR] = 0,5 p.a. je předpoklad",
 463                 "dsr_sensitivity_scenarios": dsr_sens, "latency_plus_5m_info": latency,
 464                 "walk_forward_note": "roční stabilita fixní varianty vybrané na 2020-02…2022; pro 2021–22 NE čistý OOS",
 465                 "robustness": robust, "gap_audit": audit, "verdict": verdict}
 466      (out / "results.json").write_text(json.dumps(payload, indent=1, default=str))
 467      with open(out / "trades.csv", "w", newline="") as fh:
 468          w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["period"])
 469          w.writeheader()
 470          w.writerows(rows)
 471      if (out / "trades.csv").stat().st_size > 50 * 2 ** 20:  # limit souborů GitHubu
 472          import gzip
 473          with open(out / "trades.csv", "rb") as src, gzip.open(out / "trades.csv.gz", "wb") as dst:
 474              dst.write(src.read())
 475          (out / "trades.csv").unlink()
 476      print("SUMMARY", json.dumps({"chosen": ctag, "verdict": verdict, "track_a": track_a, "track_b": track_b,
 477                                   "robust": robust, "dsr": dsr["dsr"], "dsr_sens": dsr_sens, "neighbors": nb,
 478                                   "latency_val_x2": latency["validation"]["x2"]["net_pnl"],
 479                                   "val": res["validation"], "final": res["final_test"], "tuning": res["tuning"],
 480                                   "bh_val": bh["validation"]["x1"], "bh_final": bh["final_test"]["x2"],
 481                                   "wf": {k: v["net_pnl"] for k, v in wf.items()}}, default=str))
 482  
 483  
 484  if __name__ == "__main__":
 485      main()
````

## D3. tests/test_spot_led.py (`e77f2f9`)
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
````

## E. Skutečný výstup testů
CI GitHub Actions: PR #29 run 42252402404 → `33 passed in 0.31s`, `RUN_REQUEST chybí - jen testy`; PR #30 run 42252674818 → `25 passed in 0.16s`, `RUN_REQUEST chybí - jen testy`.
Lokálně `pytest -v` (PR #29 + DSR):
````
test_funding_dispersion.py::test_selection_longs_lowest_shorts_highest PASSED [  3%]
test_funding_dispersion.py::test_signal_uses_only_settled_rates_up_to_decision PASSED [  6%]
test_funding_dispersion.py::test_prefix_invariance_of_decisions PASSED [  9%]
test_funding_dispersion.py::test_funding_cashflow_sign_and_boundaries PASSED [ 12%]
test_funding_dispersion.py::test_costs_scale_linearly PASSED       [ 15%]
test_funding_dispersion.py::test_short_leg_liquidation_at_double_price PASSED [ 18%]
test_funding_dispersion.py::test_long_short_pnl_and_no_overlap PASSED [ 21%]
test_funding_dispersion.py::test_skips_week_when_too_few_eligible PASSED [ 24%]
test_funding_dispersion.py::test_buy_hold_and_evaluate_shapes PASSED [ 27%]
test_funding_dispersion.py::test_funding_exactly_at_entry_and_exit_is_excluded PASSED [ 30%]
test_funding_dispersion.py::test_funding_one_hour_inside_edges_is_included_once PASSED [ 33%]
test_funding_dispersion.py::test_changing_future_data_does_not_change_earlier_decisions_weights_fills PASSED [ 36%]
test_funding_dispersion.py::test_costs_charged_on_all_four_legs_entry_and_exit PASSED [ 39%]
test_funding_dispersion.py::test_vol_matched_benchmark_info PASSED [ 42%]
test_funding_dispersion.py::test_R1_repro_sparse_data_is_not_eligible PASSED [ 45%]
test_funding_dispersion.py::test_R1_missing_funding_event_inside_window_makes_ineligible_not_zero PASSED [ 48%]
test_funding_dispersion.py::test_R1_interval_change_8h_4h_1h_is_continuous PASSED [ 51%]
test_funding_dispersion.py::test_R1_duplicate_after_normalization PASSED [ 54%]
test_funding_dispersion.py::test_R2_benchmark_accounts_funding_sign PASSED [ 57%]
test_funding_dispersion.py::test_R3_gap_through_liquidation_at_exit_open PASSED [ 60%]
test_funding_dispersion.py::test_R3_high_of_exit_hour_is_not_used PASSED [ 63%]
test_funding_dispersion.py::test_R4_no_trades_still_writes_results_with_null_dsr PASSED [ 66%]
test_funding_dispersion.py::test_R4_constant_returns_dsr_undefined PASSED [ 69%]
test_funding_dispersion.py::test_B_basket_metrics_aggregate_four_legs PASSED [ 72%]
test_funding_dispersion.py::test_D_decision_after_publication_time PASSED [ 75%]
test_funding_dispersion.py::test_E_edge_funding_impact_is_quantified PASSED [ 78%]
test_deflated_sharpe.py::test_paper_numeric_example PASSED         [ 81%]
test_deflated_sharpe.py::test_single_trial_is_psr_vs_zero PASSED   [ 84%]
test_deflated_sharpe.py::test_normal_psr_closed_form PASSED        [ 87%]
test_deflated_sharpe.py::test_dsr_decreases_with_trials_and_variance PASSED [ 90%]
test_deflated_sharpe.py::test_negative_skew_and_fat_tails_lower_psr PASSED [ 93%]
test_deflated_sharpe.py::test_moments_and_from_returns PASSED      [ 96%]
test_deflated_sharpe.py::test_var_from_trials_and_errors PASSED    [100%]
````
Lokálně `pytest -v tests/test_spot_led.py` (PR #30; + 7 DSR testů = 25):
````
test_features_use_only_current_and_previous_bar PASSED [  5%]
test_long_signal_enters_next_open_and_exits_after_hold PASSED [ 11%]
test_short_signal_mirror_and_thresholds PASSED   [ 16%]
test_perp_already_moved_blocks_signal PASSED     [ 22%]
test_no_overlap_per_asset PASSED                 [ 27%]
test_missing_entry_bar_drops_signal_and_missing_exit_flags_gap PASSED [ 33%]
test_funding_only_strictly_inside_holding PASSED [ 38%]
test_prefix_invariance PASSED                    [ 44%]
test_costs_scale_and_equity_reconciles PASSED    [ 50%]
test_exit_must_stay_inside_period PASSED         [ 55%]
test_neighbors_and_gap_audit PASSED              [ 61%]
test_G_overnight_position_enters_daily_mtm PASSED [ 66%]
test_G_exit_delay_is_bounded PASSED              [ 72%]
test_G_no_exit_beyond_period_end_time_based PASSED [ 77%]
test_G_simultaneous_entries_independent_of_symbol_order PASSED [ 83%]
test_latency_sensitivity_enters_one_bar_later PASSED [ 88%]
test_buy_hold_accounts_funding_sign PASSED       [ 94%]
test_undefined_dsr_is_null_not_zero PASSED       [100%]
````

Deflated Sharpe nástroj (`tools/research/deflated_sharpe.py`) beze změny oproti předchozímu balíčku.
