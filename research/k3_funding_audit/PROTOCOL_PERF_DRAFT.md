# K3 — NÁVRH výkonnostního protokolu (DRAFT, sepsán PŘED daty o fundingu/cenách)

Stav: **NÁVRH k oponentuře ChatGPT (dialog 0261) a ke schválení vlastníkem.** Nic z tohoto se nespouští, dokud
v `dialog/OWNER_DECISIONS.md` není výslovný řádek „SCHVÁLENO: výkonnostní běh K3“. Výhradně PAPER, výzkum.
Předchozí krok: datový audit GO (`f4f8ca7`, kontrola `AUDIT.md`). Autor: Claude, 2026-11-10 11:20 UTC.
Zakázáno do schválení: stahovat hodnoty fundingu/cen nad rámec kroku 0b, počítat rozdíly, výnosy, korelace.

## Hypotéza a mechanismus
Kapitál a marže jsou mezi Binance (CEX, USDT) a Hyperliquid (DEX, USDC) segmentované ⇒ funding stejného aktiva se
může po dny lišit. Pozice: short perp na burze s vyšším fundingem, long na burze s nižším (delta ≈ 0). Rodina: carry
(DSR počítá i předchozí carry pokusy: spot_perp_carry, funding_reversal, eth_funding_extreme, FUNDING_CARRY_DELTA_NEUTRAL,
FUNDING_DISPERSION_8_PERPS, weekend_carry, btc_quarterly_carry, sol_basis_convergence).

## Krok 0b — datová brána cen (bez výkonu, smí běžet jen se schváleným krokem 1)
Denní svíčky HL (`candleSnapshot` 1d) a Binance Vision 1d klines pro 160 kvalifikujících symbolů v překryvu.
GO, pokud ≥ 20 symbolů má ≥ 95 % dní s cenou na obou burzách. Jinak DATA NO-GO (basis P/L neměřitelný) a K3 končí.

## Data a PIT
- Univerzum: 160 symbolů z `summary.json` (pár binance–hyperliquid); symbol obchodovatelný od dne, kdy má ≥ 30 dní
  historie na obou burzách; delisting na kterékoli burze = nucený výstup za poslední známou cenu ×2 skluz.
- Funding: skutečná vypořádání (Binance Vision `fundingRate` se SHA-256; HL `fundingHistory`), započtena v čase
  vypořádání. Signál v den D používá jen vypořádání s časem < D 00:00 UTC.
- Ceny: denní close obou burz (basis P/L = rozdíl změn cen obou nohou).

## Pravidla (pevná)
- Spread s(D) = součet (funding_HL − funding_BIN) za L dní před D, převedený na % p.a.
- Vstup v D 00:00 (fill = open D, tj. close D−1 + skluz), pokud |s| ≥ H; směr podle znaménka s.
- Výstup, pokud |s| < H/2, znaménko s se otočí, nebo po 60 dnech držení (pak smí okamžitě znovu vstoupit dle pravidla).
- Velikost: 1 000 USD na nohu, max 20 současných párů (výběr podle |s| sestupně), každá burza má vlastní kolaterál
  10 000 USD (páka ≤ 2× na nohu). Likvidační kontrola každé nohy zvlášť denním high/low (udržovací marže 5 %);
  likvidace jedné nohy = ztráta marže + nucené zavření druhé.
- Převod kolaterálu mezi burzami nejvýš 1× týdně, poplatek 0,1 % převáděné částky + 1 USD, dostupný až D+1.
- Mřížka (N +4): L ∈ {3, 7} dní × H ∈ {20 %, 40 %} p.a.

## Náklady
Jeden obchod = 4 exekuce (2 nohy vstup + 2 nohy výstup). Binance taker 0,05 %, HL taker 0,045 %, skluz 0,05 % na
exekuci ⇒ ×1 = 0,39 % notionalu jedné nohy za kolo; scénáře ×1/×2/×3. Funding je P/L (ne náklad), započítán skutečný.

## Dělení (chronologicky)
Ladění 2023-06-01 → 2024-12-31 · Validace 2025-01-01 → 2025-12-31 · Závěr 2026-01-01 → 2026-10-31 (otevře se jednou).

## Benchmarky
Hotovost 0 % i 4 % p.a. (USDC/T-bill proxy); B&H BTC (jen pro kontext rizika); single-venue carry Binance (short perp
+ long spot, stejná mřížka H) jako test, zda mezi-burzovní varianta přidává něco navíc.

## Kritéria (všechna, jinak zamítnuto)
K1 hrubá hrana (funding + basis před náklady) v ladění ≥ 3× náklad ×1 · K2 validace ×2 net > 0 a > hotovost 4 % ·
K3 ×3 v validaci ≥ 0 · K4 Sharpe validace ×2 ≥ 1,0 · K5 závěr ×2 > 0 · K6 max DD ≤ 15 % · K7 žádný symbol > 30 % P/L ·
K8 DSR ≥ 0,95 s N z registru (aktuálně 218 + 4) · K9 soused v mřížce se stejným znaménkem ×2 v validaci.
Splnění = jen „kandidát pro forward PAPER ≥ 60–90 dní“, nikdy „zisková strategie“.

## Výstupy
`trades.csv` (obě nohy, funding, poplatky), `results.json`, `RESULTS.md`, nezávislý přepočet souhrnů z trades.csv,
SHA-256 všech archivů, běh přes GitHub Actions.

## Rizika mimo model (reportovat, nemodelovat)
Default/zmrazení burzy (FTX 2022), depeg USDT/USDC, změna pravidel fundingu (strop HL), geo/regulatorní dostupnost.

## DODATEK 1 (2026-11-10 13:30 UTC, po oponentuře ChatGPT 0262; stále PŘED daty o hodnotách fundingu/cen)
Mění návrh výše; při rozporu platí tento dodatek. Stále NESCHVÁLENO k výkonu.
1. **Krok 0b = hodinová brána (nahrazuje denní).** Pro primární simulaci se vyžaduje PIT hodinová cesta mark/index
   (nebo last) na OBOU burzách + hodinová vypořádání fundingu HL a skutečná vypořádání Binance, synchronizace časových
   razítek ±1 min. Měří se jen časová razítka a pokrytí, ne hodnoty. GO: ≥ 20 symbolů s ≥ 548 dny hodinového pokrytí
   ≥ 95 % na obou burzách. Jinak **DATA NO-GO pro výkon** (žádná interpolace z denních close); denní konzervativní
   odhad smí být jen diagnostika bez kandidátního verdiktu. Známé riziko: HL `candleSnapshot` vrací jen posledních
   ~5 000 svíček (1h ≈ 208 dní) a placené archivy (requester-pays S3) jsou zakázané ⇒ očekávaný výsledek NO-GO, ověří se.
2. **Ledger po nohách v měně kolaterálu** (Binance USDT, HL USDC), převod přes USDC/USDT kurz (Binance Vision spot
   `USDCUSDT` 1h), oddělené margin účty, haircut kolaterálu, poplatky a limity výběru, scénář „převod zmrazen“
   (žádný rebalancing po celou dobu stresu).
3. **Univerzum zmrazené as-of** začátku každého období; delisting/survivorship: audit kroku 0 bral HL `meta` k dnešku ⇒
   před výkonem doplnit historicky delistované symboly obou burz, jinak ve verdiktu uvést survivorship bias.
   Stratifikace: celý vzorek vs symboly s ≥ 730 dny.
4. **Stres USDC depeg 2023-03** (10.–13. 3. 2023) jako explicitní scénář; jeden incident nekvantifikuje budoucí tail.
5. **Basis/MTM obou noh hodinově, margin/ADL/likvidační cesta každé nohy**, přesné intervaly vypořádání při změnách.
6. **Benchmark úročení:** kromě 0/4 % i dosažitelné úročení skutečně vázaného kolaterálu (ne risk-free).
7. **Exekuce:** 4 plnění se spreadem a depth/slippage; citlivost ×1/×2/×3; filtr hrana ≥ 3× náklad (STATE 13:38).
8. **Purge/embargo** u překrývajících se pozic, blokový bootstrap intervalů spolehlivosti, DSR N ≥ 222 (vyšší, pokud
   evidence carry rodiny vyžaduje).
9. **Interpretace:** i při splnění K1–K9 je výsledek nanejvýš „kandidát s nepojištěným rizikem protistrany/depegu“,
   nikdy prokázaná risk-adjusted hrana.
10. Zmrazení celého protokolu commitem PŘED jakýmkoli pohledem na výkonnostní výsledky; výkon jen po řádku vlastníka
    „SCHVÁLENO: výkonnostní běh K3“ v `dialog/OWNER_DECISIONS.md`.
