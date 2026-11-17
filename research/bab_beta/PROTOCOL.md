# Betting-against-beta (BAB), koš 8 USDT-M perpů, tržně neutrální — předem registrovaný protokol (2026-11-07)

Hypotéza R11 (autopilot běh #29, fronta ve `automation/STATE.md`). Výhradně PAPER výzkum podle
`automation/RESEARCH_FRAMEWORK.md` v2. Zapsáno a commitnuto **před** prvním kódem, stažením dat i výsledkem.
Po prvním spuštění se pravidla, dělení ani kritéria nemění; povoleny jsou jen dodatky k načítání dat zapsané
před zobrazením jakékoli metriky.

## Mechanismus a odlišnost od otestovaného
- Frazzini–Pedersen (2014): investoři s omezenou pákou přeplácejí aktiva s vysokou betou ⇒ nízká beta má vyšší
  výnos na jednotku rizika. Portfolio long nízká beta / short vysoká beta, nohy škálované na stejnou betu ⇒
  ex ante tržně neutrální. Výnos nezávisí na směru trhu ⇒ jediná dosavadní rodina, která může projít stopou B
  i v medvědím 2025–26 (všech 7 long-only hypotéz z 2026-11-05–07 selhalo právě tam).
- Žádná ze 110 hypotéz v `reports/hypothesis-inventory-20261105.md` ani R1–R9 neřadí podle bety:
  `beta_hedged_residual` = návrat rezidua jednoho aktiva po zajištění betou (intradenně), `cross_sectional_rotation`
  a `relative_strength` = řazení podle výnosu (long-only), `weekly_inverse_vol_basket` = váhy 1/σ (long-only),
  R8 (PR #29) = řazení podle fundingu. BAB řadí podle kovariance s trhem a drží obě strany.

## Data (veřejná, bez klíčů; stahuje GitHub Actions — síť session je pro Binance blokovaná)
- Binance Vision USDT-M perpetual: denní klines `data/futures/um/monthly/klines/<S>/1d/<S>-1d-YYYY-MM.zip`
  a funding `data/futures/um/monthly/fundingRate/<S>/<S>-fundingRate-YYYY-MM.zip`, 2020-01 … 2026-10.
- Koš (pevný, předem, stejný jako R8): BTCUSDT, ETHUSDT, XRPUSDT, SOLUSDT, BNBUSDT, ADAUSDT, DOGEUSDT, LTCUSDT.
- SHA-256 každého archivu do `data_source.json`. Chybějící měsíc PŘED prvním existujícím archivem aktiva je povolen
  (kontrakt ještě neobchodoval); chybějící měsíc po něm ⇒ chyba běhu (zastavit, dodatek).
- Chybějící jednotlivý den: aktivum je v rozhodnutí nezpůsobilé, chybí-li den v okně bety nebo svíčka dne vstupu.
  Během držení: ocenění poslední známou close; chybí-li svíčka dne výstupu, výstup za open nejbližšího dalšího dne
  (příznak `exit_shifted=1`); chybí-li den, nekontroluje se v něm likvidace (příznak se počítá do `results.json`).

## Pravidla
- Rozhodnutí v den D (pondělí), vstup za **open dne D** (00:00 UTC). Signál používá jen denní close do **D − 2**
  včetně (1 celý den zpoždění exekuce — konzervativní).
- Denní výnos r_i,t = close_t / close_{t−1} − 1. Tržní výnos m_t = průměr r_i,t přes aktiva koše, která mají svíčky
  t i t − 1.
- Beta β_i = cov(r_i, m) / var(m) přes posledních W dní končících D − 2; vyžaduje všech W výnosů aktiva.
- Způsobilých < 6 aktiv ⇒ hotovost H dní. Jinak seřadit vzestupně podle β (shoda ⇒ abecedně), **long 3 nejnižší,
  short 3 nejvyšší**.
- Váhy: β̄_L, β̄_S = průměrné bety nohou (zdola omezené na 0,25). Surové L = 1/β̄_L, S = 1/β̄_S, přeškálovat na
  L + S = 0,60 (gross 60 % equity při vstupu, bez páky); uvnitř strany stejné váhy (L/3, S/3).
- Výstup za open dne D + H, tam hned nové rozhodnutí (D + H je opět pondělí). Bez stop-lossu, bez filtrů.
- Funding: událost s časem t, vstup < t < výstup: cash flow = −strana × sazba × qty × open denní svíčky dne t
  (long platí kladnou sazbu, short ji inkasuje). Denní cena místo hodinové = aproximace (sazby ~0,01 %).
- Likvidace short nohy: marže = notional (1×). Dosáhne-li denní high v době držení (dny vstup … výstup − 1)
  2 × vstupní ceny ⇒ ztráta nohy = notional, noha končí (`liquidated=1`). Long noha bez páky likvidaci nemá.

## Náklady
Poplatek 0,095 % + skluz 0,02 % na stranu a nohu (konzervativně nad skutečným taker poplatkem perpů, stejně jako R8),
náklady ×1 / ×2 / ×3. Funding se nenásobí.

## Mřížka a výběr (4 varianty, N +4)
W ∈ {60, 120} dní × H ∈ {7, 14} dní. Výběr jedné varianty na **ladění ×1 podle čistého zisku**; zvolená se beze změny
použije ve validaci a závěrečném testu. Sousedé = 2 varianty lišící se v jednom rozměru.

## Dělení
- Ladění 2020-10-05 … 2022-12-31; validace 2023-01-01 … 2024-12-31; závěrečný test 2025-01-01 … 2026-10-31
  (podle rámce v2 jen „druhá validace“; použít jednou, nic podle něj neladit).
- Každý blok začíná v hotovosti 10 000 USDT; první rozhodnutí = první pondělí ≥ začátek bloku; koš se otevře jen,
  když jeho výstup padne do bloku (den výstupu ≤ konec bloku).
- Walk-forward: kalendářní roky 2021, 2022, 2023, 2024 se zvolenou variantou, náklady ×2.

## Měřítko
B&H koše 8 perpů stejnými vahami (12,5 %), bez rebalance, nákup za open prvního dne bloku, prodej za close posledního,
stejné náklady, bez fundingu (konzervativně ve prospěch B&H); aktivum nedostupné na začátku bloku = hotovost.
Informačně (NE kritérium): realizovaná beta denních výnosů strategie k m_t a korelace s BTC ve validaci a závěrečném
testu; placebo „obrácený BAB“ (long vysoká, short nízká beta, stejné škálování) ×1.

## Metriky
Denní equity = 10 000 + realizovaný P/L + neuzavřený P/L noh za denní close. Sharpe = průměr / sd denních výnosů × √365.
Max DD z denní equity. „Obchod“ = jedna noha (vstup–výstup), net_pnl včetně fundingu a nákladů. PF z noh.

## Kritéria (rámec v2, beze změny)
- Stopa A: A1 validace ×1 Sharpe > B&H a max DD < B&H; A2 ≥ 30 obchodů ve validaci; A3 validace ×2 PF > 1,2 a zisk > 0;
  A4 validace ×1 zisk bez 3 nejlepších > 0; A5 závěrečný ×2 zisk > 0, Sharpe > B&H a DD < B&H.
- Stopa B: B1 validace ×2 zisk > 0 a PF > 1,2; B2 max DD ≤ 0,6 × B&H ve validaci i závěrečném testu (×1);
  B3 závěrečný ×2 zisk > 0; B4 validace ×1 bez 3 nejlepších > 0; B5 validace + závěrečný ≥ 20 obchodů; B6 ladění ×1 zisk > 0.
- Robustnost (nutná pro „kandidáta“): DSR ≥ 0,95 na denních výnosech validace ×1 (`tools/research/deflated_sharpe.py`),
  N = 166 (pracovní odhad 162 po R7 + 4 této mřížky; R10 nedokončen ⇒ DSR podmíněné), V[SR] = 0,5 p.a.;
  oba sousedé zisk ×2 ve validaci > 0; walk-forward zisk ×2 ve ≥ 3 ze 4 let.
- Prošlo vše ⇒ jen **forward PAPER ve výzkumu ≥ 60 dní**, nikdy „zisková strategie“ ani zásah do produkčních botů.

## Kontrola look-ahead (testy kódu před daty)
Rozhodnutí v D se nezmění po změně dat od D − 1 dál (prefix invariance); funding na hranách (t = vstup, t = výstup)
se nezapočte; náklady lineárně ×1/×2/×3; likvidace short nohy; ex ante beta-neutralita vah (β̄_L·L = β̄_S·S).

## Hlavní rizika
Squeeze shortované nohy (memecoiny), survivorship bias (koš vybrán v roce 2026), nestabilita bety, malý koš (3 + 3),
funding dražší na vysoko-betových aktivech v býčím trhu (short ho ale inkasuje).

## Výstupy
`trades.csv` (každá noha), `results.json`, `RESULTS.md`, `data_source.json`; řádek v `automation/STRATEGY_REGISTRY.md`;
draft PR do `research/autopilot`. Spuštění: commit UTC času do `research/bab_beta/RUN_REQUEST`.

## Dodatek 0 (2026-11-07, před stažením jakýchkoli dat a před první metrikou)
Chybí-li svíčka dne výstupu, noha se uzavře za **poslední známou close před dnem výstupu** (místo open dalšího dne) —
výstup tak zůstane v hranicích bloku a nová noha se neotevírá dřív, než stará skončí. Příznak `exit_shifted=1` zůstává.
Funding se u takové nohy počítá do 00:00 dne výstupu jako obvykle. Ostatní pravidla beze změny.
