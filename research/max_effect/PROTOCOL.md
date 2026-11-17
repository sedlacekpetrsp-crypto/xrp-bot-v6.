# MAX efekt („loterijní“ aktiva), koš 8 USDT-M perpů, tržně neutrální — předem registrovaný protokol (2026-11-07)

Hypotéza R12 (fronta ve `automation/STATE.md`). Výhradně PAPER výzkum podle `automation/RESEARCH_FRAMEWORK.md` v2.
Zapsáno a commitnuto **před** kódem, stažením dat i jakýmkoli výsledkem. Po prvním spuštění se pravidla, dělení
ani kritéria nemění; povoleny jsou jen dodatky k načítání dat zapsané před zobrazením jakékoli metriky.
Spuštění backtestu až **2026-11-08 UTC** (limit max. 3 nové hypotézy/den; 2026-11-07 vyčerpán R5, R7, R11).

## Mechanismus a odlišnost od otestovaného
- Bali–Cakici–Whitelaw (2011): aktiva s extrémním maximálním denním výnosem v nedávné minulosti („loterie“)
  jsou investory s preferencí kladné šikmosti přeplácena ⇒ následně podvýnosná. Pro krypto popsáno
  (Li–Shen–Xue–Zhang 2021, „Cryptocurrency anomalies and economic constraints“; Grobys–Junttila 2021).
  Portfolio short vysoký MAX / long nízký MAX, dolarově neutrální.
- Řadí podle extrému rozdělení denních výnosů (pravý chvost), ne podle bety (R11, PR #32), výnosu/momenta
  (`cross_sectional_rotation`, `relative_strength`, R13), vzdálenosti od ročního maxima (R5, PR #28), fundingu (R8)
  ani volatility (`weekly_inverse_vol_basket`). Žádná ze 110 hypotéz v `reports/hypothesis-inventory-20261105.md`
  ani R1–R11 nepoužila MAX.
- Oproti R11 nižší obrat (H ≥ 14 dní): R11 ukázal, že týdenní obrat 8 perpů s 0,115 % na stranu sežere hranu ~1–3 % p.a.

## Data (veřejná, bez klíčů; stahuje GitHub Actions — síť session je pro Binance blokovaná)
- Binance Vision USDT-M perpetual: denní klines `data/futures/um/monthly/klines/<S>/1d/<S>-1d-YYYY-MM.zip`
  a funding `data/futures/um/monthly/fundingRate/<S>/<S>-fundingRate-YYYY-MM.zip`, 2020-01 … 2026-10.
- Koš (pevný, předem, stejný jako R8): BTCUSDT, ETHUSDT, XRPUSDT, SOLUSDT, BNBUSDT, ADAUSDT, DOGEUSDT, LTCUSDT.
- SHA-256 každého archivu do `data_source.json`. Chybějící měsíc PŘED prvním existujícím archivem aktiva je povolen
  (kontrakt ještě neobchodoval); chybějící měsíc po něm ⇒ chyba běhu (zastavit, dodatek).
- Chybějící jednotlivý den: aktivum je v rozhodnutí nezpůsobilé, chybí-li den v okně bety nebo svíčka dne vstupu.
  Během držení: ocenění poslední známou close; chybí-li svíčka dne výstupu, výstup za open nejbližšího dalšího dne
  (příznak `exit_shifted=1`); chybí-li den, nekontroluje se v něm likvidace (příznak se počítá do `results.json`).

- Shodná data, loader, ocenění, funding, likvidace a ošetření mezer jako R11 (`research/bab_beta/PROTOCOL.md`
  včetně Dodatku 0: chybí-li svíčka dne výstupu, uzavřít za poslední známou close před dnem výstupu).

## Pravidla
- Rozhodnutí v den D (pondělí), vstup za **open dne D**. Signál jen z denních close do **D − 2** včetně.
- Denní výnos r_i,t = close_t / close_{t−1} − 1. **MAX_i = max r_i,t přes posledních L dní končících D − 2**;
  vyžaduje všech L výnosů aktiva a svíčku dne D (jinak nezpůsobilé).
- Způsobilých < 6 aktiv ⇒ hotovost H dní. Jinak seřadit vzestupně podle MAX (shoda ⇒ abecedně),
  **long 3 nejnižší MAX, short 3 nejvyšší MAX**.
- Váhy: dolarově neutrální, každá noha 0,10 equity (gross 60 %, long 30 % / short 30 %), bez páky, bez beta škálování.
- Výstup za open dne D + H, tam hned nové rozhodnutí (D + H je opět pondělí). Bez stop-lossu, bez filtrů.
- Funding a likvidace short nohy (denní high ≥ 2 × vstupní fill ⇒ ztráta notional) přesně jako R11.

## Náklady
Poplatek 0,095 % + skluz 0,02 % na stranu a nohu, ×1 / ×2 / ×3. Funding se nenásobí.

## Mřížka a výběr (4 varianty, N +4)
L ∈ {14, 28} dní × H ∈ {14, 28} dní. Výběr jedné varianty na **ladění ×1 podle čistého zisku** (shoda ⇒ první v pořadí
L14_H14, L14_H28, L28_H14, L28_H28); zvolená se beze změny použije ve validaci a závěrečném testu. Sousedé = 2 varianty
lišící se v jednom rozměru.

## Dělení
- Ladění 2020-10-05 … 2022-12-31; validace 2023-01-01 … 2024-12-31; závěrečný test 2025-01-01 … 2026-10-31
  (použít jednou, nic podle něj neladit).
- Každý blok začíná v hotovosti 10 000 USDT; první rozhodnutí = první pondělí ≥ začátek bloku; koš se otevře jen,
  když jeho výstup padne do bloku.
- Walk-forward: kalendářní roky 2021, 2022, 2023, 2024 se zvolenou variantou, náklady ×2.

## Měřítko
B&H koše 8 perpů stejnými vahami bez rebalance a bez fundingu (stejné jako R11). Informačně (NE kritérium):
realizovaná beta k m_t (průměr výnosů koše) a korelace s BTC; placebo „obrácený MAX“ (long vysoký, short nízký) ×1.

## Metriky
Denní equity = 10 000 + realizovaný P/L + neuzavřený P/L noh za denní close. Sharpe = průměr / sd denních výnosů × √365.
Max DD z denní equity. „Obchod“ = jedna noha, net_pnl včetně fundingu a nákladů. PF z noh.

## Kritéria (rámec v2, beze změny, shodná s R11)
- Stopa A: A1 validace ×1 Sharpe > B&H a max DD < B&H; A2 ≥ 30 obchodů ve validaci; A3 validace ×2 PF > 1,2 a zisk > 0;
  A4 validace ×1 zisk bez 3 nejlepších > 0; A5 závěrečný ×2 zisk > 0, Sharpe > B&H a DD < B&H.
- Stopa B: B1 validace ×2 zisk > 0 a PF > 1,2; B2 max DD ≤ 0,6 × B&H ve validaci i závěrečném testu (×1);
  B3 závěrečný ×2 zisk > 0; B4 validace ×1 bez 3 nejlepších > 0; B5 validace + závěrečný ≥ 20 obchodů; B6 ladění ×1 zisk > 0.
- Robustnost (nutná pro „kandidáta“): DSR ≥ 0,95 na denních výnosech validace ×1, **N = 170** (pracovní odhad 166 po R11
  + 4 této mřížky; R10 nedokončen ⇒ DSR podmíněné), V[SR] = 0,5 p.a.; oba sousedé zisk ×2 ve validaci > 0;
  walk-forward zisk ×2 ve ≥ 3 ze 4 let.
- Prošlo vše ⇒ jen **forward PAPER ve výzkumu ≥ 60 dní**, nikdy „zisková strategie“ ani zásah do produkčních botů.

## Kontrola look-ahead (testy kódu před daty)
Prefix invariance rozhodnutí v D vůči datům od D − 1; MAX odpovídá ručnímu výpočtu; nezpůsobilost při mezeře;
dolarová neutralita a gross 60 %; funding na hranách se nezapočte; náklady lineárně; likvidace short nohy;
součet net_pnl v trades.csv = P/L bloku.

## Hlavní rizika
Squeeze shortované nohy (vysoký MAX = často memecoin v hype), survivorship bias koše, malý koš (3 + 3),
MAX koreluje s volatilitou a betou (částečný překryv s R11 — informačně porovnat).

## Výstupy
`trades.csv` (každá noha), `results.json`, `RESULTS.md`, `data_source.json`; řádek v `automation/STRATEGY_REGISTRY.md`;
draft PR do `research/autopilot`. Spuštění: commit UTC času do `research/max_effect/RUN_REQUEST`.
