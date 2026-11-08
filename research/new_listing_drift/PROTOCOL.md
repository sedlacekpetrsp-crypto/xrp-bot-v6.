# A1 NEW-LISTING DRIFT — short nově listovaných USDT-M perpů — předem registrovaný protokol (2026-11-08)

Fronta A (STATE.md, rozhodnutí 2026-11-08 13:38; dohoda HUNT-01 s ChatGPT 0211/0221). Výhradně PAPER výzkum podle
`automation/RESEARCH_FRAMEWORK.md` v2. Zapsáno a commitnuto **před** kódem, stažením cen i jakýmkoli výsledkem.
Po prvním spuštění se pravidla, dělení ani kritéria nemění; povoleny jsou jen dodatky k načítání dat zapsané před
zobrazením jakékoli metriky. Žádný automatický short „každého listingu“ v produkci — jde jen o test hypotézy.

## Mechanismus a odlišnost od otestovaného
- Nově listované tokeny mají vysoké počáteční ocenění, nízký float a plánované odemykání (unlock) ⇒ v řádu měsíců
  po listingu systematicky podvýnosné (literatura k IPO underperformance; pro krypto listingy např. Ante 2019,
  Benedetti–Kostovetsky 2021 pro ICO). Hrana = průřez stáří listingu, ne cenový indikátor.
- Žádná ze 110 hypotéz inventáře ani R1–R13 nepracovala s datem listingu ani s košem > 8 aktiv (filtr z atribuce PR #36).
- Koš: celá historie Binance Vision USDT-M včetně delistovaných (PIT inventura PR #38, `listings.csv`, `bb7f4b5`).

## Data (veřejná, bez klíčů; stahuje GitHub Actions)
- Univerzum: `research/new_listing_inventory/listings.csv`, řádky `eligible_a1 = True` a `first_day ≥ 2020-02-01`
  (leden 2020 = začátek archivu, ne skutečný listing ⇒ vyřazen). Omezení: filtr `eligible_a1` používá i informace
  z prvních 180 dní (mezery, recyklovaný ticker, funding) — týká se 18 symbolů (~2,6 %); uvedeno jako omezení.
- Ceny: `data/futures/um/monthly/klines/<S>/1d/<S>-1d-YYYY-MM.zip` od měsíce `first_day` do měsíce
  min(first_day + 185 dní, 2026-10-31); funding `data/futures/um/monthly/fundingRate/<S>/...` stejné měsíce.
  BTCUSDT 1d celé 2020-01 … 2026-10 (placebo a B&H). SHA-256 každého archivu + kontrola `.CHECKSUM` do `data_source.json`.
- Obchodní den = svíčka s objemem > 0 (dodatek 1 inventury). Chybějící archiv uvnitř okna ⇒ listing vyřazen
  s důvodem v `results.json` (počet se reportuje); > 2 % vyřazených ⇒ běh je neplatný (dodatek před metrikami).

## Pravidla
- Pro listing s `first_day = L`: vstup **short za open dne E = L + K** (kalendářní dny). Není-li v E obchodní den,
  posun na nejbližší obchodní den ≤ E + 3, jinak listing přeskočen. Je-li `last_day < E`, listing nelze obchodovat
  (počítá se jako „delist před vstupem“, bez P/L).
- Výstup za **open dne X = L + T**. Není-li X obchodní den: nejbližší obchodní den ≤ X + 3, jinak close posledního
  obchodního dne před X. **Nucený výstup při delistingu**: je-li `last_day < X`, uzavřít za close `last_day`
  (příznak `forced_delist`).
- Velikost: každá pozice notional **100 USDT = 1 % počátečních 10 000 USDT**, bez skládání; max. **100 současně
  otevřených pozic** v bloku (gross ≤ 100 % počátečního kapitálu); nový vstup při plné kapacitě se přeskočí (počet
  se reportuje). Pořadí vstupů téhož dne abecedně.
- Likvidace short nohy (konzervativně, izolovaná 1×): denní high ≥ 2 × vstupní fill v kterémkoli dni držení
  (včetně dne vstupu, mimo den výstupu za open) ⇒ ztráta celého notional + vstupní poplatek, pozice uzavřena ten den.
- Funding: short dostává `+sazba × qty × open dne události` (záporná sazba = platí) pro události entry_ms < t < exit_ms.
  Funding se nenásobí cenovými multiplikátory nákladů.

## Náklady
Poplatek 0,095 % + skluz **0,05 %** na stranu (vyšší než u majorů — malé, mladé kontrakty), ×1 / ×2 / ×3.

## Mřížka a výběr (4 varianty; N = 198 + 4 = **202**)
K ∈ {30, 60} dní × T ∈ {90, 180} dní (držení 30–150 dní). Výběr jedné varianty na **ladění ×1 podle čistého zisku**
(shoda ⇒ pořadí K30_T90, K30_T180, K60_T90, K60_T180). Zvolená beze změny ve validaci a závěrečném testu.
Sousedé = 2 varianty lišící se v jednom rozměru.

## Dělení (chronologicky podle data listingu)
- Ladění: L ∈ 2020-02-01 … 2022-12-31; validace: L ∈ 2023-01-01 … 2024-12-31; závěrečný test: L ∈ 2025-01-01 …
  2026-04-30 (použít jednou, nic podle něj neladit). Pozice bloku mohou trvat přes konec bloku (portfolio bloku žije
  do posledního výstupu).
- Každý blok = samostatné portfolio od 10 000 USDT; denní equity = 10 000 + realizovaný P/L + neuzavřený P/L za denní
  close (poslední známá close) + naběhlý funding, od prvního vstupu do posledního výstupu.
- Walk-forward: listingy podle kalendářních let 2021, 2022, 2023, 2024 se zvolenou variantou, ×2.

## Měřítka
1. **BTC-short placebo** (kritérium): identický rozvrh (stejné dny vstupu/výstupu, notional, náklady, funding BTCUSDT),
   short BTCUSDT místo listingu ⇒ odliší hranu listingu od prostého shortu trhu.
2. **B&H BTCUSDT** přes stejné kalendářní okno bloku (rámec v2; Sharpe a max DD), 10 000 USDT.
3. Hotovost (0). Informačně: zajištěná varianta = strategie − placebo (short listing / long BTC).

## Metriky
Sharpe = průměr / sd denních výnosů equity × √365; max DD z denní equity; „obchod“ = jedna pozice, net_pnl včetně
fundingu a nákladů; PF z obchodů; hrubá hrana = průměr (entry_fill − exit_fill)/entry_fill před poplatky a fundingem.
Informačně: podíl P/L z 5 nejlepších obchodů, počet likvidací, nucených delistingů, přeskočených kvůli kapacitě.

## Kritéria (rámec v2; short kniha ⇒ stopa B + placebo)
- C1 validace ×2: čistý zisk > 0 a PF > 1,2.
- C2 validace ×2: čistý zisk > BTC-short placebo ×2.
- C3 validace ×1: zisk bez 3 nejlepších obchodů > 0.
- C4 validace ×1: Sharpe > B&H BTC a max DD ≤ B&H BTC.
- C5 závěrečný test ×2: čistý zisk > 0 a > placebo ×2.
- C6 ≥ 30 obchodů ve validaci.
- C7 ladění ×1: hrubá hrana na obchod ≥ 3 × náklad round-trip ×1 (≥ 0,87 %) — požadavek rozhodnutí 2026-11-08.
- Robustnost (nutná pro „kandidáta“): DSR ≥ 0,95 na denních výnosech validace ×1, N = 202, V[SR] = 0,5 p.a.;
  oba sousedé validace ×2 zisk > 0; walk-forward ×2 zisk > 0 ve ≥ 3 ze 4 let.
- Prošlo vše ⇒ jen **forward PAPER ≥ 60–90 dní ve výzkumu**, nikdy „zisková strategie“ ani zásah do produkce.

## Kontrola look-ahead (testy kódu před daty)
Rozhodnutí o vstupu závisí jen na L a datech ≤ E (prefix invariance vůči svíčkám po E); výstup a delisting jen
z dat ≤ dne výstupu; funding na hranách (t = entry_ms, t = exit_ms) se nezapočte; náklady lineárně v multiplikátoru;
likvidace short; kapacita 100; součet net_pnl v trades.csv = P/L bloku; placebo používá stejný rozvrh.

## Hlavní rizika
Squeeze mladých tokenů (likvidace), dostupnost výpůjčky/limity pozic (archiv neobsahuje), skutečná cena při delistingu
(settlement) se může lišit od poslední close, koncentrace P/L v několika kolapsech, režimová závislost (bear 2022).

## Výstupy
`trades.csv`, `results.json`, `RESULTS.md`, `data_source.json`; nezávislý přepočet souhrnů z trades.csv; řádek
v `automation/STRATEGY_REGISTRY.md`; draft PR do `research/autopilot`. Spuštění: commit UTC času do
`research/new_listing_drift/RUN_REQUEST`.
