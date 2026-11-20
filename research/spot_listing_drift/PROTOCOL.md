# A5 SPOT-LISTING DRIFT — short USDT-M perpu po pozdějším spot listingu na Binance — předem registrovaný protokol (2026-11-09)

Výhradně PAPER výzkum podle `automation/RESEARCH_FRAMEWORK.md` v2 (rozhodnutí 2026-11-08 13:38: nové hypotézy povoleny,
filtr hrana ≥ 3× náklad; STATE 2026-11-09: po DATA NO-GO A3 vybrat novou hypotézu proti registru). Zapsáno a commitnuto
**před** kódem, stažením cen i jakýmkoli výsledkem. Po prvním spuštění se pravidla, dělení ani kritéria nemění; povoleny
jen dodatky k načítání dat zapsané před zobrazením jakékoli metriky. Žádný zásah do produkce.

## Mechanismus a odlišnost od otestovaného
- Od 2023 Binance často listuje USDT-M perp **dříve** než spot. Pozdější spot listing je veřejná událost s náběhem
  pozornosti a nákupů před ním (oznámení, airdropy/launchpool, market-making) ⇒ hypotéza „sell the news“: po zahájení
  spot obchodování cena v řádu dní až týdnů klesá (literatura k listing efektům burz: abnormální výnos kolem oznámení,
  negativní drift po listingu).
- Nová událost: v registru (inventář 110 + R1–R13 + A1–A4) nikdo nepracoval se **spot listingem existujícího perpu**.
  A1 (PR #39) testoval stáří **perp** listingu (vstup 30–60 dní po něm, držení 30–150 dní) — jiná událost, jiný horizont;
  A5 není varianta A1 (žádná změna stopu, zajištění ani okna A1). Riziko příbuznosti (listingová rodina, short mladých
  tokenů ⇒ squeeze) přiznáno; hlavní kontrola = BTC-short placebo a likvidační pravidlo převzaté beze změny z A1.

## Data (veřejná, bez klíčů; stahuje GitHub Actions)
- Perp univerzum: `research/new_listing_inventory/listings.csv` (PR #38, `bb7f4b5`), všechny řádky s `reused_ticker = False`
  (bez ohledu na `eligible_a1`).
- Spot listing den S: S3 výpis `data/spot/monthly/klines/` (Binance Vision); spot symbol = perp symbol; pokud neexistuje
  a perp začíná `1000000`, `1000` nebo `1M`, zkusí se symbol bez prefixu (v tomto pořadí). S = první den s objemem > 0
  v nejstarším měsíčním archivu `…/<SPOT>/1d/<SPOT>-1d-YYYY-MM.zip`. Spot ceny se k ničemu jinému nepoužijí.
- Událost platí, pokud: perp `first_day ≤ S − 7` (perp obchodovatelný ≥ 7 dní před spotem), `2020-02-01 ≤ S ≤ 2026-09-30`
  a perp `last_day ≥ S`.
- Perp ceny: `data/futures/um/monthly/klines/<P>/1d/` a `fundingRate` od měsíce S do měsíce min(S + 40 d, 2026-10-31);
  BTCUSDT 1d + funding 2020-01 … 2026-10 (placebo, B&H). SHA-256 každého archivu + `.CHECKSUM` do `data_source.json`.
- Obchodní den = svíčka s objemem > 0. Chybějící perp archiv uvnitř okna ⇒ událost vyřazena (počet reportován);
  > 2 % vyřazených ⇒ běh neplatný.

## Pravidla
- Vstup **short za open dne E = S + K** (S je znám nejpozději na konci dne S ⇒ K ≥ 1 bez look-ahead). Není-li E obchodní
  den perpu, nejbližší obchodní den ≤ E + 3, jinak událost přeskočena.
- Výstup za **open dne X = S + T**; není-li obchodní den, nejbližší ≤ X + 3, jinak close posledního obchodního dne před X;
  delisting perpu (`last_day < X`) ⇒ nucený výstup za close `last_day`.
- Velikost 100 USDT notional = 1 % z 10 000 USDT, bez skládání, max. 100 současných pozic, vstupy téhož dne abecedně.
- Likvidace short (izolovaná 1×): denní high ≥ 2 × vstupní fill v kterémkoli dni držení (mimo den výstupu za open) ⇒
  ztráta celého notional + vstupní poplatek. Funding: short dostává `+sazba × qty × open dne události`, entry < t < exit.
- Mechanika (fill, funding, equity, metriky) = kód A1 PR #39 beze změny, liší se jen událost a okna.

## Náklady
Poplatek 0,095 % + skluz 0,05 % na stranu, ×1 / ×2 / ×3; funding se nenásobí.

## Mřížka a výběr (4 varianty; N = 214 + 4 = **218**)
K ∈ {1, 3} dny × T ∈ {10, 30} dní. Výběr na ladění ×1 podle čistého zisku (shoda ⇒ pořadí K1_T10, K1_T30, K3_T10,
K3_T30); zvolená beze změny ve validaci a závěrečném testu. Sousedé = 2 varianty lišící se v jednom rozměru.

## Dělení (chronologicky podle S, podle počtu událostí — zvoleno předem, protože počet událostí před 2023 neznáme)
Platné události seřazené podle (S, symbol): prvních 40 % = **ladění**, dalších 30 % = **validace**, posledních 30 % =
**závěrečný test** (zaokrouhlení: n_tun = round(0,4 n), n_val = round(0,3 n)). Hranice se zapíší do `results.json`.
Závěrečný test použít jednou; je-li v 2025–26 (známý režim), smí jen zamítnout. Každý blok = samostatné portfolio
10 000 USDT; walk-forward ×2 po kalendářních letech S s ≥ 10 událostmi (informační, viz robustnost).
Pojistka: < 60 platných událostí celkem ⇒ **STOP bez metrik výkonu** (DATA NO-GO, reportuje se jen počet).

## Měřítka
1. BTC-short placebo se stejným rozvrhem (kritérium). 2. B&H BTCUSDT přes okno bloku (Sharpe, DD). 3. Hotovost.
Informačně: hrubý výnos tokenu v oknech S−7…S (náběh) — jen popis, ne kritérium.

## Kritéria (rámec v2; short kniha)
- C1 validace ×2: čistý zisk > 0 a PF > 1,2.
- C2 validace ×2: čistý zisk > BTC-short placebo ×2.
- C3 validace ×1: zisk bez 3 nejlepších obchodů > 0.
- C4 validace ×1: Sharpe > B&H BTC a max DD ≤ B&H BTC.
- C5 závěrečný test ×2: čistý zisk > 0 a > placebo ×2.
- C6 ≥ 30 obchodů ve validaci.
- C7 ladění ×1: hrubá hrana na obchod ≥ 3 × náklad round-trip ×1 (≥ 0,87 %).
- Robustnost (nutná pro kandidáta): DSR ≥ 0,95 na denních výnosech validace ×1 (N = 218, V[SR] = 0,5 p.a.); oba
  sousedé validace ×2 > 0; walk-forward ×2 > 0 ve ≥ 2/3 let s ≥ 10 událostmi.
- Prošlo vše ⇒ jen forward PAPER ≥ 60–90 dní ve výzkumu; nikdy „zisková strategie“.

## Kontrola look-ahead (syntetické testy před daty)
Vstup závisí jen na S a datech ≤ E; S z prvního spot dne s objemem > 0; událost vyžaduje perp first_day ≤ S − 7;
dělení podle pořadí S; ostatní mechanika = testy A1 (funding na hranách, náklady lineárně, likvidace, kapacita, placebo).

## Hlavní rizika
Squeeze malých tokenů, oznámení spot listingu předchází S (část pohybu už proběhla — test měří jen drift po S),
nepřesná shoda tickerů (prefix 1000), recyklované spot tickery, malý počet událostí před 2023.

## Výstupy
`trades.csv`, `results.json`, `RESULTS.md`, `events.csv` (S, perp, spot symbol), `data_source.json`; nezávislý přepočet
z trades.csv; řádek v registru; draft PR do `research/autopilot`. Spuštění: commit UTC času do `RUN_REQUEST`.
