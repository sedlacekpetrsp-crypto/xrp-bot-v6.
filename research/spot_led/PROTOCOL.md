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

## Dodatek 3 (2026-11-06 ~17:05 UTC, pokyn vlastníka; před výpočtem výkonnosti)
- `RUN_REQUEST` začínající `AUDIT` ⇒ jen `data_audit.json` (mezery 5m, přechody `funding_interval_hours` a nesoulady rozestupu
  pro sémantiku A i B), žádná výkonnost.
- Výkonnost se odmítne (kód 3, `PERFORMANCE_REFUSED`) ještě před stažením dat, pokud ve složce chybí `FUNDING_SEMANTICS.json`
  (`semantics` A/B, `evidence`, `decided_utc`) nebo neodpovídá implementaci (A).

## Dodatek 4 (2026-11-06 ~17:20 UTC, rozhodnutí o sémantice; výkonnost dál nespuštěna)
- Audit run 42256137116 (commit `3b5a838`; automatická zpráva chybně říká „backtest results“, obsahuje jen `data_audit.json`
  a `data_source.json`): BTCUSDT / ETHUSDT / XRPUSDT 2020-01…2026-10 bez jediného přechodu `funding_interval_hours`
  (A i B 0 nesouladů). 5m mezery: BTC/ETH spot 462, perp 288 chybějících svíček; XRP spot 462, perp 1 728.
- Sémantika převzata z auditu PR #29: **B s tolerancí změny uprostřed úseku** (`FUNDING_SEMANTICS.json`); kód přepnut z A na B.
  Pro tato 3 aktiva jsou A i B v datech totožné.
- Zámek výkonnosti vyžaduje `performance_hold = false`; zapsané rozhodnutí má `true` (pokyn vlastníka) ⇒ výpočet odmítnut.

## Dodatek 5 (2026-11-06, oponentura kol 4–6 ChatGPT/Claude; výkonnost dál nespuštěna, návrh na kontrolu)
- **Brána výkonnosti (bod 5).** Režim explicitní: `RUN_REQUEST` začíná `AUDIT` nebo `PERF`, jinak kód 4 bez metrik.
  Před načtením dat musí `FUNDING_SEMANTICS.json` obsahovat i `audit_id`, `impl_sha256` (otisk `spacing_ok`,
  `funding_chain_gaps`, `funding_window`, `funding_completeness`; vypíše `--print-fingerprints`) a `data_manifest_sha256`
  z auditu. Po načtení a před první simulací se otisk načtených archivů porovná s auditovaným; neshoda ⇒ kód 3, nic se
  nezapisuje. Audit nevolá simulaci a v `audit_manifest.json` označí staré výkonnostní soubory jako cizí.
- **Opožděný nákup benchmarku (bod 2).** Každé aktivum má vlastní skutečný čas nákupu; funding se účtuje pro
  vstup_aktiva < t < prodej (`funding_window`, totožné se strategií: dřív benchmark filtroval od t0 a započetl i událost
  přesně v opožděném vstupu).
- **Úplnost fundingu benchmarku (bod 1).** Nesouvislosti, odhad chybějících událostí a neznámé pokrytí pro každé držené
  aktivum (3 aktiva), z x1 každého období. Chybějící sazba se nedosazuje nulou.
- **Registr datových závad (bod 3).** Explicitní třídy `blocking`/`informational`; neregistrované počítadlo ⇒ chyba.
  Nově blokují `funding_price_fallbacks` benchmarku (dřív jen exportováno) a závady fundingu benchmarku. Výstupy zpožděné
  v limitu 60 min (dodatek 1) jsou informativní. Podmínka latence +5 min zůstává samostatná.
- **Nevyplněné vstupy (bod 4).** Signál bez vstupní svíčky se eviduje (`unfilled_entries`, aktivum, strana, časy,
  plánovaný notional z equity v portfolio simulátoru, důvod) bez pozice, poplatku a cooldownu; > 0 ⇒ blokující závada.
- Zapsané rozhodnutí nová pole nemá a `performance_hold` zůstává `true` ⇒ výkonnost dál odmítnuta; uvolní jen vlastník.

## Dodatek 6 (2026-11-06, oponentura kola 8; výkonnost dál nespuštěna, návrh na kontrolu)
- **Zamítnutí a vadný benchmark.** `BENCHMARK_DEPENDENCY`: A1 ← validace, A5 ← finální test, B2 ← validace + finální test,
  ostatní kritéria benchmark nepoužívají (ověřeno testem změnou benchmarku po obdobích); neznámé kritérium = závislé na všech
  obdobích. Neprošla-li žádná stopa a některá stojí jen na kritériích s vadným benchmarkem ⇒ NEROZHODNUTO. Selhání
  robustnosti ⇒ ZAMÍTNUTO. Latence +5 min zůstává podmínkou kandidáta. Závady strategie zamítnutí zatím nemění.
- **Otisk implementace** = sha256 normalizovaného AST celého `run.py` + `tools/research/deflated_sharpe.py` (bez komentářů
  a docstringů) + Python major.minor.
- **Duplicitní řádky** (funding i svíčky): stejná hodnota se počítá (`duplicate_rows_same_value`, informativní), jiná ⇒ chyba
  načtení. Dřív se tiše přepsala pozdější hodnotou.
- **Prázdné držení** nehlásí mezeru. **Souběh a atomicita** jako v PR #29 (zámek `.run.lock` ⇒ kód 5, workflow
  `concurrency`, atomické zápisy, `run_id` a hashe v `audit_manifest.json`, `trades_sha256` v `results.json`).

## Dodatek 7 (2026-11-06, kolo 9; výkonnost dál nespuštěna, návrh na kontrolu)
- **Rozhodování (Q1/Q3)** přes sdílený `tools/research/decision_gate.py`, totožný s PR #29: závislosti kritérií na
  datech strategie i benchmarku, robustní testy podle zasažených dat a foldů, globální závady ladicího období ⇒ NEROZHODNUTO.
  Latence +5 min zůstává dodatečnou podmínkou kandidáta.
- Nová blokující závada `signal_bars_lost_to_gaps`: 5m časy období bez příznaku (chybí spot/perp svíčka T nebo T − 5 min).
  Chybějící svíčky jinak tiše ruší signály, a tím mění výběr obchodů.
- **Zámek** `fcntl.flock`, **audit** do `audits/<UTC>_<run_id>/` (jako PR #29).
- **Nezávislý ekonomický přepočet** (Decimal, bez importu runneru): 3 obchody (long s fundingem, short se sizingem
  z realizované equity, long přes půlnoc s MTM) a benchmark, shoda na 1e-6 USDT.
- **Provozní otisk (Q2):** `ops_sha256` = sha256 bajtů `PROTOCOL.md` a workflow. Jakákoli změna ⇒ rozhodnutí o výkonnosti
  neplatí.
- **Audit reálných dat (run 42268957661):** BTC/ETH spot 462, perp 288 chybějících 5m svíček; XRP perp 1 728, spot_only
  3 268. Bez duplicit, bez přechodů intervalu fundingu, sémantika B s tolerancí 0 nesouladů. Otisk dat shodný s auditem
  3b5a838 (reprodukovatelné).
