# K7 — FOMC announcement premium v BTC — PŘEDREGISTRACE VÝKONNOSTNÍHO TESTU (NÁVRH)

Stav: **NAVRŽENO, NESPUŠTĚNO** (autopilot běh #51, 2026-11-11 07:20 UTC). Commitnuto PŘED jakýmkoli výpočtem
výnosů kolem událostí. Navazuje na krok 0 (`PROTOCOL.md` + dodatek 1, run 42968402155 → `b390f35`: 69 způsobilých FOMC).
**Výkon se spustí jen po splnění OBOU:** (a) řádek vlastníka „SCHVÁLENO: výkonnost K7“ v `dialog/OWNER_DECISIONS.md`;
(b) oponentura ChatGPT tohoto protokolu (dialog 0281+) a případný dodatek commitnutý před výpočtem. Výhradně PAPER.

## 1. Literární audit (stručný, poctivě s omezeními)
- Savor & Wilson (2013, JFQA): výnos akcií v dny plánovaných makro oznámení výrazně vyšší (announcement risk premium).
- Lucca & Moench (2015, JF): S&P 500 v 24 h před FOMC ≈ +0,49 % (1994–2011), mimo okno ~0.
- Kurov, Wolfe & Gilbert (2021, Finance Research Letters 40, „The disappearing pre-FOMC announcement drift“):
  po roce 2015 drift v akciích prakticky zmizel ⇒ **prior pro období 2018–2026 je slabý**.
- Krypto: nalezeny jen práce/teze o reakci BTC na FOMC (např. Emerald JOIC-12-2020-0048, teze Univ. Vaasa) a
  publicistika; **plné texty nečteny ⇒ tvrzení z nich nepřebírám**. Systematický důkaz pre-FOMC driftu v BTC neznám.
- Důsledek: test je převážně **falzifikační**; očekávaný výsledek je spíš nulový. Nic se neladí podle výsledku.

## 2. Hypotézy
- H0 (nulová): průměrný log-výnos BTC v okně události − průměr párovaného placeba = 0 (a po nákladech ≤ 0).
- H1 (jednostranná, směr předem): pre-okno > placebo (risk premium / pre-FOMC drift). Post-okno se testuje
  oboustranně (reakce na surprise nemá předem známý směr; long-only ho jen měří).

## 3. Data a události (zmrazeno z kroku 0)
- Události: 69 FOMC z `step0_events.csv` (`pit_status=PROVEN`, realizováno, pokrytí 100 %); čas t = 14:00
  America/New_York → UTC (konvence; citlivost: varianta t = 14:30 ET pro rok ≥ 2011 tisková konference — jen
  diagnostika, nepoužívá se k výběru).
- Ceny: Binance Vision **USDT-M perp BTCUSDT 1h** klines (monthly zip + CHECKSUM, SHA-256 přes Actions); pro
  události před dostupností perpu (do 2019-09) spot BTCUSDT 1h se stejnými náklady perpu. Funding: Binance Vision
  `fundingRate` (long platí kladný funding při každém 8h vyrovnání uvnitř okna); před 2019-09 konzervativně
  +0,03 %/8 h.
- Chronologické dělení (podle pořadí událostí, pevně): ladění 1.–35., validace 36.–51., závěrečný 52.–69. (18).

## 4. Varianty (pevně 4, žádná další mřížka) — long BTC perp v okně, jinak hotovost, 1× páka, 10 000 USDT
| ID | Okno (vstup open svíčky → výstup open svíčky) |
|---|---|
| PRE24 | t−24 h → t |
| PRE2 | t−2 h → t |
| POST2 | t → t+2 h |
| POST24 | t → t+24 h |
Výběr „zvolené“ varianty jen v ladění (max čistý zisk ×1); validace/závěrečný test se jen vyhodnotí. N pro DSR =
218 (registr) + 4 = **222**.

## 5. Náklady
Stejně jako A1/A2: fee 0,095 % + skluz 0,05 % za obchod (round trip), ×1/×2/×3; navíc pro POST okna kvůli
rozšířenému spreadu kolem oznámení skluz ×2 už v základu (konzervativně). Funding podle bodu 3.

## 6. Placebo a benchmarky
- **Párované placebo:** pro každou událost 20 pseudo-časů ze stejného dne v týdnu a stejné UTC hodiny v předchozích
  26 týdnech (jen minulost), mimo ±72 h od jakékoli FOMC a mimo ±24 h od CPI (termíny CPI jen ke kontrole
  překryvu, z BLS archivu, nejsou součástí signálu), ve stejném vol režimu (kvartil 30d realizované vol počítané
  jen z dat před událostí). Statistika: výnos události − průměr jejího placeba.
- **Benchmarky:** B&H BTC téhož segmentu; hotovost; exposure-matched náhodná okna (stejná délka, stejný počet).
- **Clustery/překryv:** reportovat FOMC s CPI v ±24 h a události ve víkendovém/svátkovém okně; diagnostika, ne filtr.

## 7. Síla testu (spočítáno před daty z předpokladu, ne z událostí)
Předpoklad: σ výnosu BTC ≈ 3,5 % / 24 h a ≈ 1,0 % / 2 h. Jednostranně α = 5 %, síla 80 %:
| okno | n = 69 MDE | ±95 % CI | závěrečný n = 18 MDE |
|---|---|---|---|
| 24 h | 1,05 % | 0,83 % | 2,05 % |
| 2 h | 0,30 % | 0,24 % | 0,59 % |
Náklad ×2 ≈ 0,29 % / obchod; brána „hrubá hrana ≥ 3× náklad“ ⇒ ≥ 0,44 % / událost. **Závěr: test zachytí jen
velký efekt (≥ ~1 % / 24 h, tj. 2× akciový Lucca–Moench v bodech); malý efekt zůstane neprokazatelný.** To je
předem přijaté omezení — negativní výsledek = „nenalezeno při této síle“, ne vyvrácení.

## 8. Kritéria (předem; rámec v2)
- Stopa A i B podle `automation/RESEARCH_FRAMEWORK.md`; navíc **K7-specifické**: (i) hrubá hrana zvolené
  varianty v ladění ≥ 3× náklad ×1; (ii) výnos − placebo ve validaci > 0 a jednostranné p < 0,05
  (bootstrap 10 000 přes události); (iii) závěrečný test ×2 > 0 (smí jen zamítnout); (iv) DSR ≥ 0,95 s N = 222;
  (v) sousední okno (PRE24↔PRE2, POST2↔POST24) stejné znaménko ve validaci ×2.
- Malý počet obchodů (validace 16, závěrečný 18 < 30) ⇒ stopa A kritérium „≥ 30 obchodů“ nesplnitelné; rozhoduje
  stopa B + K7 kritéria. Případné „prošlo“ = jen forward PAPER (další FOMC: ~8/rok ⇒ forward je velmi pomalý,
  uvést výslovně).
- Falzifikace: (ii) nesplněno nebo ×2 ≤ 0 ve validaci ⇒ ZAMÍTNUTO, žádné ladění oken, času ani filtrů.

## 9. Výstupy
`trades.csv` (event_id, varianta, vstup/výstup, cena, funding, náklady ×1/×2/×3), `placebo.csv`, `results.json`,
`RESULTS.md`, nezávislý přepočet souhrnů z `trades.csv`, SHA-256 všech archivů, řádek v `STRATEGY_REGISTRY.md`.

---
## DODATEK 1 (2026-11-11, autopilot dialog, podle oponentury ChatGPT 0282) — ZAMYKÁ PROTOKOL, MÁ PŘEDNOST PŘED §2–§8
Commitnuto PŘED jakýmkoli výpočtem výnosů. Výkon stále **NESPUŠTĚN** a blokován do řádku vlastníka „SCHVÁLENO: výkonnost K7“.

### D1. Jediný primární endpoint (nahrazuje výběr ze 4 variant v §4)
- **PRE24\*** = long BTCUSDT perp, vstup open svíčky 1h v **t − 25 h**, výstup open svíčky v **t − 1 h** (24 h expozice,
  výstup hodinu PŘED oznámením). Důvod: konvence 14:00 ET, DST, případná odchylka času zveřejnění ani tisková
  konference 14:30 nemohou okno kontaminovat; rozhodnutí o obchodu je známo ≥ 29 dní předem (PIT lead z kroku 0).
- Statistika události e: **D_e = R_net(e) − mean_k R_net(placebo_e,k)**, kde R_net = log-výnos − poplatky − skluz − funding
  ve scénáři ×2 (základ). Jednotka inference = **datum FOMC** (placebo se průměruje uvnitř události).
- PRE2, POST2, POST24 a varianta t = 14:30 ET: **pouze exploratorní diagnostika**, bez kandidátní brány, bez vlivu na verdikt.
  PRE2/POST2 se počítají jen pro události s per-event doloženým časem zveřejnění (řádek „For release at …“ ze
  stránky statementu, krok 0c – jen data, zatím NEPROVEDEN); jinak událost v diagnostice abstain.

### D2. Inference (nahrazuje §8 (ii) a doplňuje §6)
- Bootstrap **přes události** (10 000, převzorkují se celé události včetně jejich placeba), citlivost: blokový bootstrap
  **po kalendářních letech** (9 bloků). Uvádí se 90% oboustranný CI (= jednostranný 95%) střední hodnoty D.
- Placebo: §6 platí; vol kvartil jen z dat před pseudo-časem (žádná budoucí volatilita); výběr pseudo-časů deterministický
  (seed = hash event_id), zmrazen před výpočtem; žádné přepárování po výsledku. Překryv placebových zásob sousedních
  událostí se reportuje (diagnostika).
- Multiplicita: primární test je jediný; DSR s N = 222 (registr 218 zkoušek + 4) zůstává doplňkovou bránou.

### D3. Minimální ekonomicky relevantní efekt a pravidlo verdiktu (nahrazuje §8)
- **MEE = 0,44 % / událost** (= 3× round-trip náklad ×1, filtr „hrana ≥ 3× náklad“).
- **GO → jen forward PAPER** (žádný kandidát pro produkci): všechna současně – (1) dolní mez 90% CI D > 0 (event i roční
  bootstrap); (2) bodový odhad D ≥ MEE; (3) průměr R_net PRE24\* ×2 > 0 a ×3 > 0; (4) D > 0 v ≥ 6 z 9 let;
  (5) závěrečný úsek (události 52–69) D ×2 > 0; (6) podvzorek s pozorovaným fundingem (≥ 2019-09, 56 událostí) splní (1)
  a (2) samostatně; (7) max drawdown kapitálové křivky PRE24\* ×2 ≤ 25 % a nejhorší jednotlivý obchod reportován;
  (8) DSR ≥ 0,95 s N = 222.
- **NO-GO (ZAMÍTNUTO)**: horní mez 90% CI D < MEE (ekonomicky relevantní efekt vyloučen) nebo bodový D ≤ 0.
- **INCONCLUSIVE**: vše ostatní (např. D > 0, ale CI zahrnuje 0 i MEE). Žádný kandidát, žádné ladění oken/času/filtrů,
  žádné další varianty; jen záznam do registru. Nulový nález ≠ důkaz absence malé hrany (§7).

### D4. Náklady a vykonatelnost (doplňuje §5)
- Vstup i výstup taker (market) za open svíčky; fee 0,095 % + skluz 0,05 % round trip ×1/×2/×3; základ ×2.
- Funding: pozorovaný z Binance Vision; před 2019-09 (13 událostí, spot ceny) modelová domněnka 0,03 %/8 h — výsledky se
  vykazují **zvlášť** pro 69 (vše) a 56 (pozorovaný funding, perp ceny).
- Páka 1×, bez likvidace; gap risk se reportuje jako rozdělení výnosů 1h svíček v okně (min, 1. percentil).
- Exploratorní POST okna: skluz ×2 v základu (beze změny).

### D5. Co se NEMĚNÍ
Události (69), PIT, dělení 35/16/18 (jen reportování podle segmentů), zdroje dat, výstupy §9. Žádné další dodatky po výpočtu.
