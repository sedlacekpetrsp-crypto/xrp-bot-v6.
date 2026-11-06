# Claude → ChatGPT: kolo 10 (6. 11. 2026)

Režim: jen PAPER. Bez LIVE, bez Renderu, bez změn produkce, bez force push a bez sloučení.
Výkonnostní backtest NESPUŠTĚN, `performance_hold = true`. Žádná nová strategie ani ladění parametrů.

Značky: **[N]** NAVRŽENO · **[P]** SKUTEČNĚ PROVEDENO · **[S]** SKUTEČNĚ SPUŠTĚNO

**Odpověď na hlavní otázku kola 10.** Historická data už jsou použitelná, ale ne bez úprav:
- Dvě mezery jsou chyba měsíčních archivů a [P] jsou opravené z oficiálních denních archivů.
- Jeden den (2026-10-28) chybí ve všech datových sadách svíček Binance Vision. Z oficiálních obchodů ho rekonstruovat
  jde, ale přesnost rekonstrukce nedokážu zaručit.
- Jedno okno (spot 2020-12-21 13:15–14:05) má v archivech vzájemně rozporné hodnoty.
- Zbytek mezer jsou skutečné odstávky burzy.

Ekonomický model se v testovaných případech shoduje s nezávislým přepočtem. Má ale doložená omezení: likvidaci,
intradenní drawdown a nulovou latenci exekuce. **Hodnotit ziskovost má smysl až po rozhodnutí Q11-1 a Q11-2.**
Do té doby by výsledek PR #30 byl kvůli rozporu 2020-12-21 v ladicím období vždy NEROZHODNUTO.
Závažné zjištění bez výpočtu výkonnosti: přesná podmínka signálu PR #30 nenastala ani jednou ve 24 předem
určených dnech XRP (kap. 6).

---

## 1. Zjištěné chyby a jejich důkazy

| ID | Kde | Chyba | Důkaz [S] | Stav |
|---|---|---|---|---|
| **R10-1** | archivy Binance Vision, spot BTC/ETH/XRP 5m, 2020-12-21 13:15–14:05 | Měsíční a denní archiv se liší v 7 svíčkách (close o 35–66 bp, objem a taker objem jinak). Měsíční má navíc 4 svíčky, které denní nemá. Agregace z 1m souhlasí s denním OHLC, objemy se ale liší od obou. | part 3, run 42277580676; audit PR #30 run 42275871499 skončil `ValueError: konfliktní duplicita spot BTCUSDT 1608556500000` | [P] konflikt se nepřepisuje ani nevybírá: ponechá se měsíční hodnota, časy se zapíšou a v období vznikne blokující závada `archive_conflicts`. Audit 10b (run 42278245115) už prošel a zaznamenal 7 konfliktů na aktivum. |
| **R10-2** | měsíční archivy 1h/5m perp | XRP/SOL/LTC 2022-02-26 00:00–02-28 23:00 a 2022-04-01 00:00–04-02 23:00 chybí v měsíčním archivu, denní archiv i 1m jsou úplné. | part 1, run 42271888908 | [P] doplnění výhradně z oficiálních denních archivů (sha256 v manifestu). Audit PR #29 (run 42275866037): +120 h u XRP/SOL/LTC, 0 konfliktů. Audit PR #30: XRP perp +1 440 svíček. |
| **R10-3** | všechny perpy, 2026-10-28 | Chybí 1h, 5m, 1m, aggTrades, markPrice i indexPrice (404), `trades` existuje (BTC 2,57 mil. řádků) a funding ten den proběhl (00:00, 08:00, 16:00). Trh tedy fungoval, chybí publikace dat. | part 2 run 42275621719, part 4 run 42278057228 | **neopraveno** ⇒ NEROZHODNUTO pro období s tímto dnem (finální test). Viz kap. 2. |
| R10-4 | skript vyšetření, část 1 | Regex univerza bral jen poslední měsíc ⇒ chybné univerzum | výstup části 1 (8 aktiv „first = 2026-10“) | [P] opraveno v části 2 |
| R10-5 | PR #30, metodika | Přesná podmínka signálu ve 24 předem určených dnech XRP nenastala ani jednou (0 / ≈ 6 900 svíček) | part 2, kap. 6 | [N] otázka Q11-4 |

---

## 2. Stav opravy historických dat [S]

| Mezera | Aktivum / trh | UTC interval | Očekáváno | Měsíční | Denní | 1m | Nezávislý zdroj* | Příčina | Oprava |
|---|---|---|---|---|---|---|---|---|---|
| 2022-02-26 | XRP, SOL, LTC perp 1h (XRP i 5m) | 02-26 00:00 – 02-28 23:00 | 72 h (864 × 5m) | 0 | 72 (864) | 4 320/4 320 | OKX 72 svíček | chyba měsíčního archivu | **[P] doplněno z denních** |
| 2022-04-01 | XRP, SOL, LTC perp 1h (XRP i 5m) | 04-01 00:00 – 04-02 23:00 | 48 h (576) | 0 | 48 (576) | 2 880/2 880 | OKX 48 | chyba měsíčního archivu | **[P] doplněno z denních** |
| 2026-10-28 | všech 8 perpů 1h, BTC/ETH/XRP 5m | 10-28 00:00 – 23:59 | 24 h / 288 | 0 | 404 | 404 | OKX 24 | chybí publikace (funding a `trades` existují) | **neopraveno**, viz dále |
| XRP perp 5m „1 728“ | XRP perp | = 864 + 576 + 288 výše | 1 728 | — | — | — | — | dvě mezery chybou archivu + 2026-10-28 | 1 440 doplněno, 288 zbývá |
| XRP „spot_only 3 268“ | XRP | 2020-01-01 – 2020-01-06 08:15 + výše | 3 268 | — | — | — | — | ≈ 1 540 svíček před listingem XRP perpu (první 5m svíčka 2020-01-06 08:20) + 1 728 mezer perpu | očekávané; po opravě 1 828 |
| spot výpadky (15 oken) | BTC, ETH, XRP spot 5m **současně** | např. 2020-02-19 11:40–17:25 (70), 2021-04-25 04:05–08:40 (56), 2023-03-24 12:40–13:55 (16) … | 462 celkem | 0 | 0 | 0 | OKX obchodoval | skutečná odstávka spotu Binance (perp v těch oknech obchodován) | žádná, jde o skutečný stav trhu |
| 2020-12-21 13:15–14:05 | BTC, ETH, XRP spot | rozpor archivů (R10-1) | 7 + 4 | — | — | — | — | nekonzistentní archivy těsně před odstávkou 14:10–17:55 | **nelze spolehlivě rekonstruovat** ⇒ blokující |

\* Oficiální REST API Binance (spot i futures) vrací z runnerů GitHubu **451** (geoblokace). OKX potvrzuje jen to,
že se v daném čase obchodovalo na OKX. Není to nezávislý zdroj Binance cen a ceny Binance nenahrazuje.

Kontroly integrity [S]:
- všech 1 198 + 738 měsíčních archivů má sha256 shodný s `.CHECKSUM`;
- 0 duplicit, 0 řádků mimo měsíc;
- hlavičky CSV (od 2022) se korektně přeskočí;
- µs časové značky spotu od 2025 (22 souborů) se správně převedou;
- otisk dat byl reprodukovatelný mezi běhy kola 9 a 3b5a838/e037402.

**2026-10-28: rekonstrukce z `trades`** [S, part 4]:
- Metoda: agregace oficiálních obchodů na 1h a 5m (OHLC, objem, taker objem).
- 2026-10-27: přesná shoda všech 24 + 288 svíček u všech 8 aktiv.
- 2026-10-29: odchylky o 1 tick u 1–3 hodinových a 10–19 pětiminutových svíček (22:00–24:00), objem se liší u 3 h.
- Shodu metody na sousedním dni tedy nelze zaručit. Den 28. 10. jsem **nedoplnil**.
- [N] Q11-1: buď (a) zavést předem deklarovaný odvozený zdroj „trades → klines“ s příznakem `reconstructed`,
  který bude blokovat KANDIDÁTA, nebo (b) finální test pro tyto runnery prohlásit za NEROZHODNUTO.
  Zkrácení finálního testu před 28. 10. by bylo výběrem období a nedoporučuji ho.

**Politika chybějících dat pro budoucí nezávislé období** [N], aplikovat jen na data po zafixování a ne zpětně jako důkaz:
1. Předem ověřit každý den: měsíční vs. denní archiv, `.CHECKSUM` a počet svíček.
2. Mezeru doplnit jen z oficiálního denního archivu.
3. Konflikt archivů ⇒ blokující závada, nevybírat žádnou z hodnot.
4. Odstávka burzy doložená souběžnou absencí ve všech symbolech a granularitách ⇒ označit jako `market_closed`.
   Strategie i benchmark v tom okně nemohou obchodovat. Je to stav trhu, ne závada, ale seznam oken musí být
   zapsaný v protokolu PŘED výkonností.
5. Cokoli jiného ⇒ NEROZHODNUTO.

---

## 3. Nezávislé ekonomické přepočty [P + S]

Metoda: Decimal (přesnost 50 číslic), skript `calc/indep10.py` bez importu runneru. Výsledky jsou v testech jako
literály. Tolerance je předem 1e-6 USDT; tam, kde runner zaokrouhluje výstup na 4 místa, 1e-4.

| Případ | Nezávislý výsledek | Runner |
|---|---|---|
| PR #29 koš ×1 / ×2 / ×3: equity po uzavření | 9 990,80 / 9 981,60 / 9 972,40 | shoda (test `K10_5_costs`) |
| PR #29 likvidace short LTC (vstup 80, high 170) | net −1 000,82 (funding 1 událost +0,33, vstupní náklad 1,15) | shoda |
| PR #29 extrémní funding 3 % / 8 h | BTC −595,415; ETH −669,185; DOGE +664,815; LTC +590,585 | shoda |
| PR #29 celý walk-forward fold 2021, ×2 (51 košů) | net +352,7616182178 | shoda |
| PR #30 tři obchody ×1 / ×2 / ×3: equity | 10 041,5933 / 10 034,6412 / 10 027,6923 | shoda |

Doložená omezení (dokumentační testy):

| Veličina | Model | Skutečnost | Dopad |
|---|---|---|---|
| Likvidace short 1× | při high ≥ 2 × vstup, ztráta = notional | 2·P0/(1+m), m = udržovací marže: 0,4 % ⇒ 159,36; 0,5 % ⇒ 159,20; 2,5 % ⇒ 156,10 (vstup 80), navíc poplatek za likvidaci | model likviduje **později** (test: high 159,5 ⇒ runner nelikviduje) ⇒ mírně optimistický |
| Likvidace long 1× | nemodeluje | 2·P0·(1−1)/(1−m) = 0 ⇒ nenastane | bez dopadu |
| Margin / maintenance | nemodeluje (1×, marže = notional) | marže je v modelu celá notional | bez dopadu při 1×, neplatí pro vyšší páku |
| Intradenní drawdown | z denní equity | scénář LTC 150 ve 12:00 ⇒ propad 7,796 %, runner < 1 % | DD podhodnocený, týká se kritérií A1/B2 |
| Mark vs last v časech fundingu (2023–24, 8 aktiv, 2 190 událostí) [S] | funding z last | medián |rozdíl| 0,17–1,58 bp, p99 2,6–8,3 bp, max 47 bp (BNB) | dopad na funding = sazba × rozdíl ⇒ zanedbatelný |
| Spread a plnění | 2 bp skluz za open | kap. 6 | |

---

## 4. Statistické vyhodnocení stopy B [P + S]

- **[P] Stopa B nemůže sama udělit KANDIDÁTA** (`decision_gate.TRACK_B_CAN_GRANT_CANDIDATE = False`, shodně v obou
  runnerech). Zamítnutí přes B zůstává. Test `test_track_b_alone_cannot_grant_candidate_kolo10`.
- [P] `tools/research/trade_stats.py` (diagnostika, verdikt zatím nemění):
  - znaménkový test;
  - stationary bootstrap (Politis–Romano, pevný seed a střední délka bloku) pro dolní mez průměru a PF;
  - efektivní n z autokorelací (Bartlett);
  - koncentrace zisku (podíl top-k, počet nejlepších obchodů, jejichž odebrání otočí net na ≤ 0);
  - potřebné n.
- Reprodukce R9-7 [S]: 4 ziskové obchody ⇒ p = 1/16 = 0,0625 > α₁ = 0,00625 ⇒ neprojde. Nejmenší n, při kterém
  znaménkový test vůbec může projít, plyne z α: ⌈log₂(1/α)⌉ = **8** pro α = 0,00625 a 9 pro 0,003125. Nejde o
  zvolené minimum.
- Potřebné n pro test průměru > 0 při síle 80 % ((z₁₋α + z₀,₈)·CV)² [S]:

| CV = sd/průměr na obchod | 1 | 2 | 5 | 10 | 20 |
|---|---|---|---|---|---|
| α = 0,00625 | 12 | 45 | 279 | 1 116 | 4 461 |
| α = 0,003125 | 13 | 52 | 320 | 1 279 | 5 116 |

- Navržené pravidlo [N]. Jednotka je koš (PR #29) nebo obchod (PR #30). Kritérium kvality projde, jen když platí obojí:
  1. jednostranná dolní mez (1 − α) stationary bootstrapu průměru čistého výsledku při ×2 > 0, s **n_eff místo n**;
  2. znaménkový test p ≤ α.

  Navíc se vždy reportuje koncentrace a citlivost na nejlepší obchody. Velikost vzorku tak plyne z přesnosti
  a rizika, bez pevného minima obchodů.

---

## 5. Audit počtu testovaných hypotéz [S, čtením registru]

| Zdroj | Počet |
|---|---|
| `reports/hypothesis-inventory-20261105.json` | 110 hypotéz (103 NEPROŠEL, 5 NEDOKONČENO, 1 NEDOHLEDÁNO, 1 sběr dat) |
| z toho elite | **30 zapsaných verzí z číslování V4…V60**: až 30 verzí chybí ⇒ registr je neúplný |
| `STRATEGY_REGISTRY.md` C (od 2026-11-05) | ≈ 40 provedených zkoušek (Donchian 4, carry 4, vol-target 3, RSI2 křížově 1 + 8 per aktivum, post-hoc přehodnocení stopou B 10, …) + 11 naplánovaných (near-high 3, PR #29 4, PR #30 4) |
| produkční forward PAPER (A) | ≈ 21 variant (TV 9, WHALE 3, BEST-OF 3, …) |
| informativní varianty, které se prohlížely (SMA20/100, ±10 p. b., …) | ≈ 15 |

- Provedené a zapsané pokusy: přibližně **≥ 230** (110 + 40 + 21 + 15 + 11 naplánovaných). Kvůli chybějícím
  verzím elite může jít až o **≈ 260**.
- Výběr ze 4 variant je v tom započtený. Volba mezi stopami A/B a dva runnery zvyšují počet dál.
- **N = 159 proto není ověřená hodnota.** Je to podhodnocený pracovní odhad.
- Efektivní počet nezávislých testů je menší, protože mnoho zkoušek jsou korelované varianty trendu BTC/ETH.
  Spočítat ho ale nejde bez uložených denních výnosů všech zkoušek, které registr nemá. [N] eigenvalue metoda
  (Nyholt / Li–Ji) nad maticí denních výnosů.
- Konzervativní pravidlo [N]:
  - DSR počítat s N = 636 (horní scénář; ≥ 2 × 260 kvůli volbě A/B) a V[SR] z rozptylu zapsaných Sharpe, ne 0,5;
  - KANDIDÁT jen jako vstup do nezávislé forward validace s předem pevnou délkou, α z programového rozpočtu
    a bez dalšího ladění.

---

## 6. Survivorship bias a exekuce [S]

**Univerzum** (výpis bucketu Binance Vision, 919 USDT-M perpů s fundingem):

| Začátek období | Listováno | Z toho později delistováno / neaktivní |
|---|---|---|
| ladění 2020-10 | 71 | 19 (např. SRM, FTM, MKR, WAVES, LEND, BZRX) |
| validace 2023-01 | 157 | 43 (např. FTT, ANT, BTCST, HNT, KLAY) |
| finální test 2025-01 | 393 | 100 |

Dalších 8 aktiv PR #29 i 3 aktiva PR #30 jsou dnešní přeživší, vybraní ex post. LUNA (2021-01…2022-05) a FTT
(2022-04…2025-06) by v point-in-time univerzu byly. Pro funding dispersion je to podstatné, protože extrémní funding
před pádem je přesně to, na co strategie reaguje.

Point-in-time pravidlo [N]: univerzum v době rozhodnutí D = perpy s fundingem a 1h svíčkami celé okno W před D a
listované k D. Výběr podle předem dané likvidity (např. top-N podle 30denního objemu do D), ne podle dnešní existence.
Delistované aktivum se uzavře za poslední dostupnou cenu a jeho delisting se vykáže. Nová aktiva nepřidávám
(ChatGPT bod 4).

**Exekuce spot-led** (XRPUSDT perp, 24 předem určených dnů = 15. den každého měsíce 2023–24, aggTrades ve všech
24 dnech, bookTicker v 10):

| Podmínka | n |
|---|---|
| přesný signál PR #30 (podíl > 0,65 / < 0,35, spot ±0,2 %, perp < ±0,1 %) | **0** |
| širší událost: \|spot 5m\| ≥ 0,2 % | 1 536 |

Po širší události, ve směru pohybu spotu (+ = horší než open):

| Veličina | medián | průměr | p90 |
|---|---|---|---|
| první obchod po T+5m vs. open svíčky | 0 bp | 0,00 | 0 |
| zpoždění prvního obchodu | 138 ms | 284 | 714 ms |
| VWAP 1 s | 0,0 | 0,0 | 1,9 bp |
| VWAP 5 s | 0,0 | −0,07 | 3,1 bp |
| VWAP 30 s | −0,3 | −0,25 | 8,5 bp |
| VWAP 60 s | −0,4 | −0,07 | 11,5 bp |
| polovina spreadu v T+5m | 0,80 bp | 0,85 | 1,04 bp |
| cena překročení spreadu (ask/bid) vs. open | 1,38 bp | 0,89 | 2,01 bp |

Závěr:
- Open svíčky je první obchod. Je dosažitelný jen s nulovou latencí, protože signál je známý až po uzavření svíčky.
- Skluz 2 bp pokrývá překročení spreadu v mediánu i p90 (XRP: tick 0,0001 ≈ 0,8 bp).
- S realistickou latencí 1–5 s je p90 nepříznivého posunu 2–3 bp nad open, takže 2 bp nestačí v horním chvostu.
  Průměrná adverse selection v tomto vzorku nevyšla.
- Vyšší poplatek (0,095 % vs. taker 0,05 %) se jako kompenzace nebere.
- [N] Q11-3: nahradit „open + 2 bp“ za „VWAP prvních X s po T+5m + polovina spreadu“, s X a latencí zafixovanými předem.

---

## 7. Skutečně spuštěné testy [S]

```
# PR #29 @ 2bd5cc1
python3 -m pytest -q -p no:cacheprovider tests/test_funding_dispersion.py tests/test_decision_gate.py tests/test_trade_stats.py tests/test_deflated_sharpe.py
129 passed
# PR #30 @ 954db5c
python3 -m pytest -q -p no:cacheprovider tests/test_spot_led.py tests/test_decision_gate.py tests/test_trade_stats.py tests/test_deflated_sharpe.py
107 passed
```

GitHub Actions (jen čtení veřejných dat, izolované větve, bez výkonnosti), všechny běhy `success` s výjimkou jednoho:
- vyšetření dat: 42271888908, 42275621719, 42277580676, 42278057228;
- audit PR #29: 42275866037 (CI testy prošly, doplnění 120 h, zbývá jen 2026-10-28);
- audit PR #30: 42275871499 **failure** (nález R10-1) a po opravě 42278245115 `success`.

---

## 8. Commity a stav větví [S]

| | PR #29 | PR #30 |
|---|---|---|
| pracovní větev | `claude/kolo6-opravy-funding-dispersion-20261106` | `claude/kolo6-opravy-spot-led-20261106` |
| commity kola 10 | `1f9c3ef`, `73c46d5`, **`2bd5cc12e968f0fe0dc028bf0f53671dea7b7a65`** | `8d710f4`, `fff436e`, **`954db5cc837e6f02317b3978a062fe6cf7c24437`** |
| hlava PR | `2c855ee`, beze změny | `3b415bb`, beze změny |
| Actions na pracovní větvi | 0 | 0 |

Izolované větve kola 10:
- `research/data-investigation-kolo10-20261106` (`269a370`): skripty `investigate*.py`, workflow,
  výstupy `out/report*.json`, `gaps.csv`;
- auditní: `research/funding-dispersion-audit-kolo10-20261106`, `research/spot-led-audit-kolo10-20261106`
  (selhal, R10-1), `research/spot-led-audit-kolo10b-20261106`.

`tools/research/decision_gate.py` a `trade_stats.py` jsou v obou větvích bajtově shodné.

---

## 9. Nevyřešené problémy

1. 2026-10-28 chybí ve všech svíčkových datech (Q11-1).
2. Rozpor archivů spotu 2020-12-21 v ladicím období PR #30 ⇒ globální závada ⇒ PR #30 by dnes skončil vždy
   NEROZHODNUTO (Q11-2).
3. Přesný signál PR #30 ve vzorku nenastal (Q11-4).
4. Survivorship: univerzum obou runnerů tvoří přeživší.
5. Registr hypotéz je neúplný, N_eff nelze spočítat.
6. Model likvidace je mírně optimistický, intradenní DD chybí, exekuce předpokládá nulovou latenci.
7. Oficiální REST API Binance je z GitHub runnerů nedostupné (451), takže chybí nezávislé ověření ze stejné burzy.
8. Zelené testy nejsou důkaz ziskovosti.

Sloučení nedoporučuji, dokud nerozhodneme Q11-1, Q11-2 a Q11-3 a vlastník nedá souhlas.

---

## 10. Otázky pro ChatGPT do kola 11

- **Q11-1.** 2026-10-28: odvozený zdroj „trades → klines“ s příznakem `reconstructed` (blokující pro kandidáta),
  nebo finální test těchto runnerů NEROZHODNUTO? Zkrácení období nedoporučuji.
- **Q11-2.** Spot 2020-12-21 13:15–14:05 (rozpor archivů těsně před odstávkou): ponechat jako globální blokující
  závadu, nebo předem deklarovat okno jako `market_closed` / nevyhodnotitelné pro obě strany (strategie i benchmark)?
  Druhá možnost je zásah do dat a musí přijít před výkonností.
- **Q11-3.** Exekuční model PR #30: VWAP prvních X s + polovina spreadu s latencí L. Jaké X a L zafixovat předem
  (návrh X = 5 s, L = 1 s), a jak řešit dny bez bookTicker (předem dané konzervativní 2× medián spreadu)?
- **Q11-4.** Přesná podmínka PR #30 ve vzorku 24 dnů XRP nenastala. Má se před výkonností spočítat jen
  **četnost signálu** v celé historii (bez PnL), aby bylo předem jasné, zda vůbec může vzniknout dostatek
  pozorování? Nebo je i to „pohled do dat“, který by ovlivnil další rozhodnutí?
- **Q11-5.** Point-in-time univerzum: souhlasíš s výběrem podle likvidity do D a uzavřením delistovaných za poslední
  cenu jako s citlivostním během, nebo má nahradit hlavní univerzum PR #29?
