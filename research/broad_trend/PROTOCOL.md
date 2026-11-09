# A2 ŠIROKÝ TREND — time-series trend + volatilitní cílení na PIT koši USDT-M perpů — předem registrovaný protokol (2026-11-09)

Fronta A (STATE.md, rozhodnutí 2026-11-08 13:38), podmínky dohod HUNT-01 (0211/0221) a HUNT-02 (0226/0227).
Výhradně PAPER výzkum podle `automation/RESEARCH_FRAMEWORK.md` v2. Zapsáno a commitnuto **před** kódem, stažením cen
i jakýmkoli výsledkem. Po prvním spuštění se pravidla, dělení ani kritéria nemění; povoleny jsou jen dodatky
k načítání dat zapsané před zobrazením jakékoli metriky.

## Mechanismus a odlišnost od otestovaného
- Time-series momentum (Moskowitz–Ooi–Pedersen 2012; pro krypto Liu–Tsyvinski 2021) s volatilitním škálováním.
- Rodina: Donchian PR #11 (4 aktiva), TS vote PR #16, VOL_MANAGED_MOMENTUM (inventář #101), R13 PR #35 (8 perpů, průřez).
  Všechny zamítnuty hlavně kritériem „pod B&H“. A2 je nová **šířkou koše (až 50 aktiv PIT, vč. delistovaných)**, ne
  mechanismem ⇒ hlavní test = **exposure-matched benchmark** (stejná časová hrubá expozice bez trendového signálu).

## Data (veřejná, bez klíčů; stahuje GitHub Actions)
- Seznam symbolů: `research/new_listing_inventory/listings.csv` (PR #38, `1bba792`), všech 923 USDT-M perpů vč.
  delistovaných. Vyřazeny jen řádky `reused_ticker = True` (10 symbolů, slepení dvou aktiv pod jedním tickerem; HUNT-02
  „žádné slepování“) — omezení: příznak je znám ex post.
- Ceny: `data/futures/um/monthly/klines/<S>/1d/<S>-1d-YYYY-MM.zip` od měsíce `first_day` do min(`last_day`, 2026-10-31).
  Funding `data/futures/um/monthly/fundingRate/<S>/...` pro symboly, které se aspoň jednou dostanou do univerza (níže),
  od prvního do posledního měsíce v univerzu (+1 měsíc). SHA-256 každého archivu + `.CHECKSUM` do `data_source.json`.
- Obchodní den aktiva = svíčka s objemem > 0. Chybějící archiv: měsíc se loguje; > 2 % chybějících kline archivů ⇒
  běh neplatný. Chybějící funding archiv u držené pozice ⇒ funding 0 a počet dní se reportuje.

## Univerzum (PIT, ke každému dni rebalance R)
Kandidát, pokud k close dne R−1 platí: (a) svíčka R−1 obchodní; (b) stáří R − `first_day` ≥ 120 dní; (c) v okně
posledních W+1 dní (W = lookback varianty) ≥ 90 % obchodních dní; (d) ne `reused_ticker`. Pořadí podle průměrného
quote objemu za 30 dní do R−1 včetně; univerzum = **top 50** (méně, pokud kandidátů < 50; počet se reportuje).
Minimální notional: Binance dnes 5 USDT ⇒ cílová pozice < 5 USDT se nezřídí (PIT lot size Binance Vision nemá — omezení).

## Signál a velikost (rebalance týdně, každé pondělí UTC)
- Signál s_i = znaménko výnosu close(R−1)/close(R−1−W) − 1. Režim **LO**: long při s = +1, jinak 0. Režim **LS**: ±1.
- σ_i = směrodatná odchylka denních log-výnosů za 30 dní do R−1, ×√365. Cílová váha w_i = s_i × (0,40 / σ_i) / n,
  n = počet aktiv v univerzu; strop |w_i| ≤ 0,10; strop hrubé expozice Σ|w| ≤ 1,0 (proporcionální zmenšení).
- Provedení: rozhodnutí z dat ≤ close R−1, **fill za close dne R** (jeden den zpoždění, konzervativně). Cílový
  notional = w_i × equity(close R); qty drženo do další rebalance (žádné denní dorovnávání). Změna |Δnotional| < 5 USDT
  se neprovádí.
- Mark-to-market denně za close. Funding denně: pozice platí `sazba × qty × close dne události` (long platí kladnou
  sazbu, short ji dostává), události v (fill, další fill]. Funding se nenásobí multiplikátorem nákladů.
- Nucený výstup: aktivum bez obchodní svíčky v den t nebo t > `last_day` ⇒ výstup za poslední známou close (příznak
  `forced_exit`), náklady se účtují; znovuvstup jen při další rebalanci.
- Likvidace short nohy (izolovaná 1×): denní high ≥ 2 × cena fillu ⇒ ztráta celého notional při ceně 2× fill, pozice zavřena.
  Long noha (≤ 10 % equity, bez páky) likvidaci nemá.

## Náklady
Poplatek 0,095 % + skluz **0,05 %** na stranu z obchodovaného notional (jako A1; koš obsahuje i menší kontrakty),
×1 / ×2 / ×3. Hrubá varianta ×0 jen pro kritérium K7.

## Mřížka a výběr (4 varianty; N = 210 + 4 = **214**)
W ∈ {50, 100} dní (pevně z literatury) × režim ∈ {LO, LS}. Výběr jedné varianty na **ladění ×1 podle Sharpe**
(shoda ⇒ pořadí W50_LO, W50_LS, W100_LO, W100_LS). Zvolená beze změny ve validaci a závěrečném testu.
Sousedé = 2 varianty lišící se v jednom rozměru.

## Dělení (bloky bez překryvu, embargo ≥ 100 dní)
- Ladění 2020-06-01 … 2022-09-22; embargo 2022-09-23 … 2022-12-31 (100 dní); validace 2023-01-01 … 2024-09-22;
  embargo 2024-09-23 … 2024-12-31; závěrečný test 2025-01-01 … 2026-10-31.
- Každý blok = samostatné portfolio od 10 000 USDT, start bez pozic (první rebalance první pondělí bloku), konec bloku
  = vše uzavřeno za close posledního dne (s náklady). Lookback smí sahat před začátek bloku (jen vstupní data).
- Walk-forward: kalendářní roky 2021, 2022, 2023, 2024 jako samostatná portfolia, zvolená varianta, ×2.
- Závěrečný test 2025–26 je režimově známý (medvědí trh) ⇒ smí **jen zamítnout**, nikdy povýšit (HUNT-02).

## Benchmarky (stejné bloky, stejný kalendář rebalance)
1. **EXPOSURE-MATCHED** (hlavní): v každé rebalanci stejná hrubá expozice G = Σ|w| jako zvolená varianta při ×1,
   rozdělená rovnoměrně long přes totéž univerzum (G/n), stejné náklady ×k, funding a nucené výstupy.
2. Equal-weight PIT koš B&H: váha 1/n long přes univerzum, týdenní rebalance, stejné náklady.
3. BTC B&H (BTCUSDT perp close, jeden vstup na začátku bloku, bez fundingu). 4. Hotovost (0).

## Metriky
Sharpe = průměr/sd denních výnosů equity × √365; max DD z denní equity; „obchod“ = epizoda pozice v jednom aktivu
(od otevření po uzavření/otočení), net_pnl = cenový P/L + funding − náklady; PF z epizod; hrubá hrana = cenový P/L
×0 celé knihy. Informačně: průměrná hrubá expozice, počet aktiv v univerzu, podíl P/L z 5 nejlepších epizod,
likvidace, nucené výstupy, obrat.

## Kritéria (zvolená varianta)
- K1 (hlavní, falzifikace HUNT-02) validace ×2: čistý zisk > 0, **Sharpe > EXPOSURE-MATCHED ×2** a čistý zisk >
  EXPOSURE-MATCHED ×2. Nesplněno ⇒ ZAMÍTNUTO.
- K2 validace ×2: PF epizod > 1,2.
- K3 validace ×1: zisk bez 3 nejlepších epizod > 0.
- K4 stopa A **nebo** B (rámec v2) vůči BTC B&H i EW koši: A = validace ×1 Sharpe i max DD lepší než oba B&H;
  B = validace i závěrečný max DD ≤ 0,6 × max DD obou B&H a ladění ×1 zisk > 0.
- K5 závěrečný test ×2: čistý zisk > 0 a Sharpe > EXPOSURE-MATCHED ×2 (jen zamítací).
- K6 ≥ 30 epizod ve validaci.
- K7 ladění: hrubý P/L ×0 ≥ 3 × celkové náklady ×1 (požadavek rozhodnutí 2026-11-08).
- Robustnost (nutná pro „kandidáta“): DSR ≥ 0,95 na denních výnosech validace ×1, N = 214, V[SR] = 0,5 p.a. (÷365);
  oba sousedé ve validaci ×2 zisk > 0; walk-forward ×2 zisk > 0 ve ≥ 3 ze 4 let.
- Prošlo vše ⇒ jen **forward PAPER ≥ 60–90 dní ve výzkumu**, nikdy „zisková strategie“ ani zásah do produkce.

## Kontrola look-ahead (testy kódu před daty)
Univerzum, signál i σ v den R závisí jen na svíčkách ≤ R−1 (prefix invariance); fill za close R; nucený výstup
jen z dat ≤ t; funding na hraně fillu se nezapočte dvakrát; náklady lineárně v multiplikátoru; strop 0,10 a Σ ≤ 1;
likvidace short; součet net_pnl epizod v trades.csv = P/L bloku; exposure-matched má stejné G jako strategie.

## Hlavní rizika
Koncentrace P/L v několika trendech (2020–21 alt sezóna), kapacita/likvidita malých kontraktů, delisting cena,
dataset bez PIT lot sizes, opotřebovaný holdout 2025–26, rodina hypotéz již několikrát zamítnuta.

## Výstupy
`trades.csv`, `equity.csv` (zvolená varianta + benchmarky), `results.json`, `RESULTS.md`, `data_source.json`;
nezávislý přepočet z trades.csv (`verify.py`); řádek v `automation/STRATEGY_REGISTRY.md`; draft PR do
`research/autopilot`. Spuštění: commit UTC času do `research/broad_trend/RUN_REQUEST`.
