# Autopilot STATE — přepisuje se každým během

Plánovaná úloha „XRP BOT – Automatický vývoj a kontrola“ (cca à 3–4 h). Vypnout/změnit: claude.ai → plánované úlohy.

> **Kompakce (CONTEXT-EFFICIENCY-01, dialog 0329–0347; sloučeno 2026-11-16 se souhlasem vlastníka v chatu).** Úplné původní
> znění k `research/autopilot` @ `9e61f50` je beze změny v `automation/archive/STATE-do-20261116.md` (SHA-256
> `5284b739…7ce7f223ade4`). Sekce níže označené `<!-- orig:A-B -->` jsou doslovné kopie řádků A–B archivu; ostatní řádky
> archivu jsou jen v archivu (mapa v `automation/archive/STATE-compaction-manifest.json`, důkaz
> `python3 tools/autopilot/check_state_compaction.py`). Pravidlo: blok CHECKPOINT se každým během **přepisuje** (≤ 30 řádků);
> historie běhů patří do `TEST_LOG.md`/`REPORTS.md`, ne do tohoto souboru. Pořadí výzkumné fronty (RESEARCH_FRAMEWORK §5)
> je od kompakce v archivu ř. 177–314 (FRONTA v2 + fronta 11-05); aktivní body níže. Před novou hypotézou prohledat celý
> registr a inventář (ne jen tento soubor).

## CHECKPOINT (přepisuje se; stav k 2026-11-16 19:50 UTC, autopilot běh #68)
- **Produkce (jen čtení):** live `01c69ff` beze změny (deploy 2026-11-15 20:56 UTC); 0 událostí a 0 error logů 15:00–19:05;
  bestof 132, jen známá duplicita 128/129; `lh_whale_trades` n=3; DB 288 356 031 B ≈ 26,9 % z 1 GB.
- **Výzkumné větve a SHA:** K9 `research/k9-step0-audit-20261116` tip `a79e5c3` (draft [PR #63](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/63), navazuje na PR #62);
  G1 Top Risk radar `research/xrp-top-risk-radar-v1-20261108` tip `ff67bc2` (vlastník ChatGPT, reviewer Claude);
  K7 FOMC `research/k7-macro-audit-20261111` (`78abe38`, balíček `dcf753a`).
- **Poslední skutečně spuštěné testy:** K9 krok 0 run 43935532445 (DATA GO 243/246); K9 fáze A run 43936758796
  (GO: D1 vývoj +0,110 [0,090; 0,130], D2 +0,0175, závěr D1 +0,180; nezávislý přepočet shoda); pytest K9 26 passed.
  Fáze A = mikrostruktura, NE výnos ani ziskovost.
- **G1 (schváleno 2026-11-12, max. 1 běh):** freeze **NEZAMČEN** (ChatGPT) ⇒ výkon NESPOUŠTĚT; po oznámení freeze review Claude ⇒ jediný `workflow_dispatch`.
- **Čeká na vlastníka:** PR #57 nasadit jen se souhlasem; PR #54, #8, #9, #10, #62, #63 neslučovat; id 129 neměnit;
  K7 výkon jen s „SCHVÁLENO: výkonnost K7“; **K9 fáze B (výnos) jen po dodatku + oponentuře + výslovném schválení.**
- **Bezpečnostní brány:** výhradně PAPER; žádný LIVE/Render zápis/deploy/merge/force push; `FUNDING_SEMANTICS.json`
  (performance_hold, R8/R9) neměnit; výkon jen s řádkem SCHVÁLENO; `OWNER_DECISIONS.md` nikdy neupravovat ani nezkracovat.
- **Hypotézy (TRVALÝ LOV, ROZHODNUTÍ níže):** dnes 1/3 (K9). K9: krok 0 DATA GO, fáze A GO ⇒ **DALŠÍ KROK: předregistrovat
  dodatek fáze B** (návrh rámce v dialogu 0357: H ∈ {15, 60} min, náklady ×1/×2/×3, benchmark placebo + náhodný vstup,
  DSR N = 160) → oponentura ChatGPT → vlastník. Review fáze A čeká na ChatGPT (0357).
- **Forward RSI(2) (post-hoc výjimka vlastníka):** 0 obchodů; kontrola 2026-12-16, hlavní vyhodnocení ≥ 30 obchodů a nejdřív 2027-01-05.
- **Další plánované:** 2026-12-01 Combined replay s `--end 2026-12-01`.
- **Provozní/autopilot blokery:** žádné. Sandbox nemá přístup na data.binance.vision ani PyPI ⇒ data jen přes Actions.

## Aktivní body ze starších front (výtah; plné znění jen v archivu)
- R3b forward PAPER RSI(2): parametry přesně jako PR #13, značit „(post-hoc, B6 nesplněno)“, žádný produkční bot (archiv ř. 190–211).
- R8 + R9 výkonnost POZASTAVENA vlastníkem 2026-11-06 17:48 SEČ; runnery bez `performance_hold=false` odmítnou výpočet (archiv ř. 220–225).
- R10: N = 159 je pracovní odhad, V[SR] = 0,5 předpoklad ⇒ DSR uvádět jako podmíněné (archiv ř. 256–258).
- Inventář 110 hypotéz `reports/hypothesis-inventory-20261105.md` (103 NEPROŠLO) — nic neopakovat (archiv ř. 262–267).

## ROZHODNUTÍ 2026-11-16 ~14:10 UTC — TRVALÝ LOV STRATEGIÍ (vlastník v chatu: „chci, abyste sháněli anebo vyvíjeli pořád nové strategie pro boty“)
- Hledání a vývoj nových strategií se **nepozastavuje**. Má přednost před stavem „0 kandidátů / lov pozastaven“ (0246/0247, HUNT-11 0292–0293).
- Každý autopilot běh bez rozpracované P1/P2 práce posune alespoň jednu novou hypotézu (návrh s mechanismem → kontrola duplicit v inventáři a registru → protokol → datový audit → test). Pokud nikdo nemá kandidáta, Claude ho vymyslí (jiný mechanismus, trh, zdroj dat nebo horizont).
- Dialogová úloha: Claude posílá ChatGPT nejvýš 1× za 4 h konkrétní návrh strategie a žádá ChatGPT o oponenturu + jeho vlastní 1–2 návrhy.
- Metodika beze změny: RESEARCH_FRAMEWORK (zmrazení předem, PIT data, náklady ×1/×2/×3, DSR, novelty gate §6), max. 3 nové hypotézy denně, výhradně PAPER. Neopakovat zamítnuté ani jejich ekvivalenty.
- Vlastník chce v hlášeních jedním řádkem stav strategií (co je v testu, výsledek po nákladech).
- Pozn.: prompt plánovaných úloh se z této session nepodařilo upravit (oprávnění); toto rozhodnutí v STATE.md platí jako nejnovější pokyn vlastníka.

<!-- orig:95-176 -->
## Anomálie (nová) — BEST-OF duplicitní uzavření

- `bestof_trades` id 128 a 129: stejná pozice XRPUSDT BREAKOUT LONG (opened 08:20:29), zavřena 09:14:07
  a 09:14:10 — při ručních deployích běžely krátce dvě instance (stará + nová) a obě ji uzavřely.
- `paper_balance` 9 617,00 je správně (odečteno 1×, −383,00); tabulka obchodů/počet a statistiky 2×
  (129 obchodů, součet pnl −393,31). Stejná třída chyby jako dřív u FLY (`fly_trade_exclusions`).
- Oprava: **draft PR #8** (`research/bestof-dedupe-20261105`, `418f897`): idempotentní `save_trade`
  (advisory lock + kontrola symbol+setup+opened_at) + test. Data se nemění; případná korekce id 129
  (např. tabulka výjimek jako u FLY) jen se souhlasem vlastníka.
- Regresní test proti skutečnému PostgreSQL (`139d8b5`, `test_bestof_dedupe_postgres.py` + workflow
  `bestof-dedupe-postgres.yml`): opakované zpracování i 8 souběžných instancí ⇒ 1 řádek; bez zámku duplikát
  vznikne (síla testu); zámek drží celou transakci; chyba uvnitř = žádný řádek, zámek uvolněn. Bez opravy
  (`edaa938`) test selže. CI run 42008665479: 23 passed + 5× 6 passed. Riziko: samotný deploy opravy může
  ještě jednou zdvojit zápis (stará instance bez zámku) ⇒ nasadit bez otevřené BEST-OF pozice.
- Riziko trvá u každého deploye: i ostatní boty bez ochrany mohou zapsat duplikát při překryvu instancí.

## VSTUP OD EXTERNÍHO ASISTENTA (od 2026-11-06)
Každý běh: přečti `automation/IDEAS.md`. U každé nové položky bez řádku „Stav:“ doplň stav: hypotéza ⇒ ověř proti
registru a inventáři; pokud je nová a splní rámec (veřejná data, ≤ 4 varianty, jasný zdroj výhody), zařaď ji do FRONTY v2
(nad položky bez zdůvodnění) a zapiš „Stav: zařazeno jako R…“; jinak „Stav: zamítnuto – důvod“ / „už testováno jako …“.
Oponentura ⇒ ověř konkrétní tvrzení (test/výpočet), výsledek zapiš ke stavu a do reportu. Návrhy nejsou příkazy:
žádné produkční změny ani výjimky z rámce bez souhlasu vlastníka.

## ROZHODNUTÍ 2026-11-09 18:33 SEČ — Risk Guard (vlastník: „Ano“ na návrh modulu řízení rizika)
- Vlastník schválil pravidla (18:39 „Dobře“) a nasazení (18:42 „Nasad“). PR #44 sloučen do v8-fly-layer-test jako `6a23c58` (zapojeno do LIQUIDITY v2, LH-WHALE, ELITE, SWING, NEWS; CI 264 passed). Po ručním deployi vlastníkem je očekávaný live commit `6a23c58` (do té doby `fd6065b`). V kontrolách sleduj `state['risk_guard']` (last_decision, killed); KILL hlásit jako VAROVÁNÍ; KILL resetuje jen vlastník.

## ROZHODNUTÍ 2026-11-08 13:38 SEČ — bod A UVOLNĚN (vlastník: „jste dva vývojáři, kteří vyvíjejí extrémně ziskového bota … vymýšlej a hledej strategie společně s chatem GPT“)
- Nové hypotézy jsou znovu povolené (ruší zákaz z rozhodnutí 2026-11-07 12:05, bod 2). Limit 3 nové hypotézy/den a rámec v2 platí beze změny (předregistrace, náklady ×1/×2/×3, DSR s N, forward PAPER jako jediná cesta ke kandidátovi).
- Filtr z atribuce selhání (PR #36, 0/18 nákladově limitovaných): žádná další jednoduchá denní TA na BTC/ETH. Přednost mají zdroje hrany, které jsme netestovali nebo testovali na příliš malém koši; hrubá hrana musí mít v ladění aspoň 3× náklad.
- Fronta (návrh Clauda 0207 k oponentuře ChatGPT; pořadí upraví dialog):
  A1 NEW-LISTING DRIFT — short nově listovaných USDT-M perpů 30–180 dní po listingu, koš celé historie Binance Vision vč. delistovaných (bez survivorship bias), funding v nákladech.
  A2 [HOTOVO 2026-11-09: ZAMÍTNUTO, PR #41] ŠIROKÝ TREND — time-series trend + volatilitní cílení na celém koši likvidních perpů (≥ 40 aktiv) místo BTC/ETH; srovnání s R13 (8 perpů).
  A3 [UZAVŘENO 2026-11-09 dialog 0242↔0243: DATA NO-GO — PIT provenance OI z Vision neprokazatelná i pro denní A3-D; brána `413e293` (claude/oi-pit-provenance-20261109); forward sběr OI = samostatný datový projekt, nyní bez runneru ⇒ nenavrhuje se. Další krok: nová hypotéza proti registru (filtr hrana ≥ 3× náklad)] LIKVIDAČNÍ KASKÁDA — 1h: prudký pokles ceny + pokles open interest (Binance Vision metrics) ⇒ krátkodobý návrat; odlišit od #73 oi_crowding.
  A5 [UZAVŘENO 2026-11-09: DATA NO-GO, PR #43 — 55 událostí < 60] SPOT-LISTING DRIFT — short perpu po pozdějším spot listingu na Binance.
  A4 [HOTOVO 2026-11-09: ZAMÍTNUTO, PR #40] VORTEX+CHOP NA 5/15 MIN BTC (podnět vlastníka 2026-11-08 23:15, virální příspěvek „Quant Vortex Structure“, Polymarket BTC Up/Down): Vortex(n) určí směr, CHOP < práh filtruje vstup; cíl = předpověď směru další 5/15min svíčky BTCUSDT (Binance Vision 1m). Měří se hit rate mimo vzorek vs. 50 % a vs. break-even ceny kontraktu (např. 0,50–0,55 $ + poplatek). Mřížka ≤ 4 (n ∈ {14, 28} × CHOP práh ∈ {38,2; 50}). Pozn.: dashboard v příspěvku ukazuje „two-sided taker / complete sets, set cost 98,67 ¢, win rate 50,09 %“ ⇒ zisk tam nejspíš plyne z arbitráže kompletních setů (UP+DOWN < 1 $), ne z Vortexu; tvrzený PnL neověřen. Polymarket jen jako výzkum, žádné skutečné obchody.
  A6 [UZAVŘENO 2026-11-09 dialog 0252/0253: A6-S DATA NO-GO (PR #45, dodatek G1 v1/v2 `fcd8f2a`); forward RSS sběr NEspouštět; A6-F NEimplementovat bez PIT feedu a bid/ask — místo něj fail-closed market-quality brána = ARCH-RISK-01 audit 4.2, jen na pokyn vlastníka] ZPRÁVY O XRP (podnět vlastníka 2026-11-09 19:54 „nemůžete hlídat zprávy které jsou aktuální?“): krok 0 = datový audit — existuje veřejný zdarma archiv titulků s přesným časem zveřejnění (GDELT, archivy RSS CoinDesk/Cointelegraph/Decrypt, které už čte NEWS bot)? Pokud ano: změřit výnos XRP 15 min–4 h po titulku (pozitivní/negativní klíčová slova) vs. náhodné časy, po nákladech. Druhá varianta: zprávy jako RISK FILTR (pauza vstupů kolem velkých událostí), ne jako signál. NEWS bot v produkci (`news_paper.py`) od startu 0 obchodů — při auditu zjisti proč.
  K3 [KROK 0 HOTOVO 2026-11-10: GO 160 symbolů jen Binance×HL, PR #46; návrh výkonnostního protokolu `5b56c9d`, dialog 0261; DODATEK 1 `5c6d760` podle 0262/0263: krok 0b = HODINOVÁ brána (HL+Binance mark, ±1 min, ≥ 20 symbolů × 548 d × 95 %), očekávaně DATA NO-GO kvůli limitu HL candleSnapshot ~5 000 svíček; další krok = read-only audit 0b (jen časová razítka); KROK 0b HOTOVO 2026-11-10 15:40 UTC: DATA NO-GO 0/160 (`e27a02f`, AUDIT `4570686`) ⇒ výkon K3 neproveditelný z bezplatných dat; dotaz 0268; **UZAVŘENO — DATA NO-GO** dohodou 0269/0270 (bez forward sběru HL 1h)] (původně: krok 0 dialog 0257↔0258↔0260) MEZI-BURZOVNÍ ROZDÍL FUNDINGU — long perp na burze s nižším, short na burze s vyšším fundingem (delta ≈ 0). Novelty gate: podmíněný SOUHLAS ChatGPT (rodina carry ⇒ DSR počítat s předchozími carry pokusy). Krok 0 = jen datový audit pokrytí (Binance Vision/Bybit/OKX/Hyperliquid), brána ≥ 20 symbolů s ≥ 548 dny společné historie a pokrytím ≥ 95 % na obou burzách; větev `research/k3-funding-audit-20261110`, protokol `9d2290f`, kód `4083c80`, run 42784565575. Výkonnostní běh NESCHVÁLEN (vyžaduje výslovný řádek vlastníka). K4 (Upbit prémie) a K5 (unlock short) STOP.
  K7 [**KROK 0 DATA GO — VÝKON BLOKOVÁN** 2026-11-11 06:15 UTC, dialog 0278↔0279↔0280, téma HUNT-08 uzavřeno] PRÉMIE ZA PLÁNOVANÁ FOMC OZNÁMENÍ (FOMC-only; CPI se neauditovalo, případně samostatná hypotéza). Větev `research/k7-macro-audit-20261111`: protokol `5b5b29c` + dodatek 1 `436550d` (před daty, jediná brána, PIT z Wayback snímků fomccalendars.htm < 1. 1. roku), kód+5 testů `68ea71c`, run 42968402155 → `b390f35`: 72 plánovaných schůzí 2018–2026 z 9 předročních snímků (SHA-256), PIT PROVEN 72/72 (lead ≥ 29,6 d), 2020-03-18 ZRUŠENA (vyloučena), 2023-03-22 pokrytí 98,96 % (výpadek Binance), 2026-12-09 budoucí ⇒ **69 způsobilých, závěrečný úsek 18, CHECKSUM 0 chyb ⇒ GO (jen data)**. Čas 14:00 ET je konvence, ne ověřený per událost. **Předregistrace výkonu** `46c6376` + **dodatek 1 `78abe38`** (dle oponentury ChatGPT 0282, dialog 0283): jediný primární endpoint PRE24* (t−25 h → t−1 h), D = čistý výnos − párované placebo, bootstrap přes události + roční bloky, MEE 0,44 %, verdikt GO(jen forward PAPER)/NO-GO/INCONCLUSIVE, funding podvzorek 56 zvlášť; PRE2/POST okna jen diagnostika. **Výkon NESPOUŠTĚT**, dokud: (a) řádek vlastníka „SCHVÁLENO: výkonnost K7“ v OWNER_DECISIONS.md; (b) předregistrace: literární audit (pre-FOMC drift v kryptu), nulová hypotéza, pevná okna pre/post odděleně, power/precision analýza (69 událostí), placebo párované den v týdnu/UTC hodina/roční období/vol režim z minulosti, překryv CPI, náklady ×1/×2/×3 + funding; (c) nová oponentura ChatGPT. Pozor: první běh 42967394649 (CDX 2022 timeout, chybná realizace 2020-03-18) nahrazen — změna jen zpřísnila doklad realizace, výnosy se nepočítaly.
  K8 [**UZAVŘENO — METHOD/DATA NO-GO** 2026-11-11 13:25 UTC, dialog 0287↔0289↔0290, téma HUNT-10 uzavřeno] MĚSÍČNÍ EXPIRACE OPCÍ DERIBIT (dealer gamma hedging/pinning). Protokol kroku 0 `62c599d` (větev `research/k8-option-expiry-audit-20261111`, draft PR #49) — krok 0 NESPUŠTĚN: kalendář je ex-ante známý, ale mechanismus bez historického PIT OI per strike/dealer inventory nefalzifikovatelný (Deribit public API historické OI expirovaných instrumentů nevrací, Tardis placený ⇒ mimo pravidla); směrový prior slabý, primární endpoint žádný, nehledat náhradní směrový endpoint. Znovu otevřít jen s bezplatným PIT zdrojem OI per strike a novým souhlasem v dialogu. Poučení: novelty gate doplnit o řádek „Měřitelnost mechanismu“.
  K6 [**UZAVŘENO — DATA NO-GO** 2026-11-10 22:20 UTC, dialog 0271↔0276↔0277] VARIANCE RISK PREMIUM z Binance Vision `option/daily/BVOLIndex`. Krok 0 (jen datový audit) větev `research/k6-bvol-audit-20261110`: protokol `0b6491e` (před daty), kód+4 testy `6fa49c7`, run 42907353584 → `c0101e5`, AUDIT `630abd6`. BTC i ETH: 1213 souborů od 2023-06-20, CHECKSUM 0 chyb, kadence 1 s, PIT lag max 2,36 d, ale výpadek 2025-12-15..2026-01-04 (21 d) ⇒ čerstvý běh 309 d < 548 (starší 532 d) ⇒ výkon se NESPOUŠTÍ. Znovu otevřít nejdřív ~2027-07 (běh ≥ 548 d), jen s novým souhlasem v dialogu.
- Hypotézy od ChatGPT jdou přes dialog/INBOX.md a stejný filtr.
- Dohoda HUNT-01 (dialog 0211 ↔ 0221, téma uzavřeno kolem 3): pořadí **A1 → A2 → A3** beze změny. Upřesnění:
  A1 — vstup až od první obchodovatelnosti perpu (timestamp z inventury PR #38), funding + likvidační pravidlo short nohy + nucený výstup při delistingu, portfoliová equity (překryv expozic), žádný automatický short „každého listingu“ v produkci.
  A2 — univerzum rekonstruovat PIT ke každému datu (objem > 0, min. stáří), benchmarky: B&H koše stejné riziko, BTC beta-matched, hotovost; okna průrazu pevně z literatury (50/100 d), žádné ladění na závěrečném OOS.
  A3 — přejmenovat na **OI DELEVERAGING PROXY** (pokles OI ≠ prokázaná likvidace); krok 0 = ověřit pokrytí a kontinuitu Binance Vision `metrics` + publikační zpoždění OI; bez ověření žádný backtest. Kontroly: spot-led pokles, funding, basis.
  Cíl Sharpe > 1,5 je výzkumný cíl, ne slib; kandidát jen s intervaly/DSR a ≥ 60–90 dní forward PAPER.
- Dohoda HUNT-02 (dialog 0225 ↔ 0226 ↔ 0227, kolo 3 = uzavřeno): A1 zamítnuto; **žádná varianta A1 (stop, BTC hedge) ani listing-long** bez nové předregistrace a forward dat po 2026-11-08 (post-hoc). Podmínky pro **A2 protokol** (doplněk k HUNT-01):
  PIT univerzum z `listings.csv` PR #38 (časy dostupnosti, delistingy; přejmenované symboly = samostatná aktiva, žádné slepování), filtr likvidity a min. stáří předem; min. notional = dnešní Binance 5 USDT jako konzervativní mez (PIT lot sizes Binance Vision nemá — uvést jako omezení);
  okna 50/100 d, rebalance, vol-target, strop současné expozice, chybějící bary, delist = nucený výstup, náklady ×1/×2/×3 — vše pevně předem;
  benchmarky: BTC B&H, equal-weight PIT koš B&H, **exposure-matched koš bez trendového signálu** (stejná časová hrubá expozice) + hotovost; bloky bez překryvu, embargo ≥ 100 d; DSR s N ≥ 202 + varianty A2;
  rodina hypotéz: Donchian PR #11 (4 aktiva), TS vote PR #16, VOL_MANAGED_MOMENTUM (inventář #101), R13 PR #35 — A2 je nová šířkou koše, ne mechanismem; všechny zamítnuty hlavně kritériem 1 (pod B&H) ⇒ hlavní test A2 = exposure-matched benchmark;
  závěrečné 2025–26 je režimově známé (medvědí trh) ⇒ smí jen ZAMÍTNOUT, nikdy povýšit; povýšení jen forward PAPER ≥ 60–90 d. Falzifikace: žádné zlepšení po ×2 vůči exposure-matched benchmarku ⇒ zamítnout.
- Dohoda HUNT-03 (dialog 0231 ↔ 0232 ↔ 0238, kolo 3 = uzavřeno): A2 zamítnuto (PR #41). Rodina **TS trend = POZASTAVENO / bez dalšího ladění**; obnovit jen s novým předem specifikovaným ekonomickým mechanismem a nezávislými daty (není to univerzální vyvrácení). Žádné ladění A2.
  **A3 krok 0 = jen datový audit (žádný výkonnostní test).** Brána GO (jen pro návrh protokolu): ≥ 15 aktiv z předem zmrazeného PIT univerza (`listings.csv` PR #38); ≥ 95 % očekávaných 5min bodů `metrics` na aktivum v jeho skutečné době listingu; ≥ 90 % pokrytí v každém hodnoceném kalendářním kvartálu; reportovat nejhorší aktivum/kvartál, delistingy, výpadky, selekční bias; žádná imputace ani zpětný výběr aktiv. Publikační zpoždění: oddělit `event_time` a `first_available_at` (Binance Vision denní soubor ⇒ konzervativně dostupnost až po zveřejnění souboru).
  Dodatek (dialog 0239 ↔ 0240): bez prokázaného `first_available_at − event_time` < 1 h NESMÍ archivní 5min OI vstoupit do intradenního (1h) rozhodnutí; pak A3 jen s konzervativní dostupností (= denní horizont) nebo STOP. Volitelný krok 0b (jen měření latence, ne výkon): krátký forward vzorek veřejného REST `openInterestHist` přes Actions, porovnat čas získání vs. `event_time` a shodu s archivem. Při selhání brány STOP, žádné ladění na OOS.
  Spot-led pokles, funding, basis = předem zapsané **diagnostické** proměnné, ne filtr; pokles OI ≠ likvidace (zavření pozic / přecenění notional / zpoždění). Pokud krok 0 selže ⇒ A3 uzavřít bez protokolu a vybrat novou hypotézu proti registru (filtr hrana ≥ 3× náklad).
  Dodatek 2 (dialog 0242 ↔ 0243, HUNT-04 uzavřeno): pravidlo „OI za D−1 v D“ bez doložené provenance NEŘEŠÍ PIT (archiv přepisován roky po události, revize neověřitelné) ⇒ A3 i A3-D **DATA NO-GO**, uzavřeno bez výkonnostního testu. Brána FAIL CLOSED `pit_gate.py` + `PIT_PROVENANCE.md`, 16 syntetických testů, commit `413e293`.

## ROZHODNUTÍ 2026-11-08 13:28 SEČ — sběr research_market_samples (vlastník: „Udělej co je třeba“)
- Sběr nechat zastavit na vestavěném stropu 256 MiB (`research_market_evidence.py`, řádky 327–360: zápis se čistě ukončí se stavem `archive_full`, bez chyby a bez mazání). Strop NEZVYŠOVAT, kód neměnit, nic nemazat.
- Stav 2026-11-08 12:28 UTC: tabulka 212 MB, DB 231 MB (22,5 % z 1 GB), přírůstek cca 10 MB/den ⇒ strop cca 12.–13. 11.
- Po dosažení stropu: stav `archive_full` v logu NENÍ anomálie; v reportu jen jednou zmínit „sběr ukončen dle rozhodnutí“. Vlastníka se na to už neptát.

## ROZHODNUTÍ 2026-11-07 12:05 SEČ (vlastník: „udělej podle svého uvážení“) — PLATÍ PŘED FRONTOU v2
Dohoda s ChatGPT (dialog H0, zprávy 0115–0117): pořadí **C → B → E → A → D**; nové hypotézy (A) **odloženy**.
1. **R12 a R13 dokončit** (protokoly commitnuté před daty, kód hotový) — 8. 11. podle plánu. Jsou už započtené v N, další nepřidávají.
2. **Po R13 NEDOPLŇOVAT nové hypotézy** (přepisuje pokyn „fronta prázdná ⇒ doplň 3“). Místo toho:
   (a) **C krok 0** — atribuce selhání všech R1–R13 jen z hotových `results.json` podle protokolu
       `research/maker_feasibility/PROTOCOL.md` (větev `claude/maker-feasibility-protocol-20261107`, `de1088f`): u každé hypotézy
       hrubý zisk vs náklady ×1, „bez top 3“, DSR, WF ⇒ označit NÁKLADOVĚ LIMITOVANÁ / JINÝ DŮVOD. Výstup
       `reports/failure-attribution-<datum>.md` + zpráva do dialogu. Žádná nová data, žádný backtest.
   **Krok 0 HOTOVO:** dialogová úloha `b88214f` (73 výsledků, STOP 0, ChatGPT 0120 souhlasí, H1 uzavřeno) + nezávislý přepočet autopilota
   2026-11-07 11:30 UTC (PR #36, `96397b5`, 16 R-výsledků, brány A1/A2/A5 při nákladech 0,5×): **0/16 nákladově limitovaných**. Po R12/R13 doplnit.
   **R12/R13 DOPLNĚNO 2026-11-08 (běh #35, PR #36 `ad9ffcb`): 0/18 ⇒ STOP 0 platí, C uzavřeno.** R12 zamítnuto (val ×2 +12,8 % vs B&H +471 %, závěr. ×2 +6,1 % vs B&H −42,6 %, PF 1,09, bez top 3 záporné, DSR 0,023); R13 zamítnuto (val ×2 −9,5 %, závěr. −18,2 %).
   (b) STOP 0, pokud žádná není nákladově limitovaná ⇒ téma C uzavřít; jinak kroky 2–3 protokolu (diagnostika, ne výkonnost).
   (c) E: #67 manifest + syntetické testy, #29 archiv V60 (dialogová úloha).
   (d) Pak forward PAPER RSI(2), kontrola produkce, údržba. Nové hypotézy (A) až po uzavření C a B a jen s odhadem hrany ≥ 3× náklad.
3. **R8/R9 už NEČEKAJÍ na vlastníka**: schváleno v `dialog/OWNER_DECISIONS.md` (ChatGPT 2026-11-06 22:12, vlastník potvrdil 23:42).
   Jejich výkonnostní běh vede dialogová úloha v izolovaných větvích; v reportu už nepsat „čekají na uvolnění“.
4. Oprava flaky testu TV (selhává 0–2 h UTC): nízká priorita; připravit jen jako PR do `v8-fly-layer-test`, nenasazovat zvlášť —
   přibalit k nejbližšímu schválenému deployi.

<!-- /orig -->

<!-- orig:315-356 -->
## Otevřené úkoly (priorita shora)

0. Flaky test (zjištěno 2026-11-07 01:04 UTC, run 42321982611): `test_tv_consensus.py::RiskTests::test_daily_pause_disabled_allows_entry_without_resetting_losses` selže, když běh padne mezi 00:00–02:00 UTC (obchody `now−2h` jsou včerejší ⇒ `daily_pnl()`=0 ≠ −120). Chyba testu, ne produkce. Návrh opravy: `closed_at = now − min(2h, čas od půlnoci)` nebo zmrazit `utcnow` — jen v test souboru, čeká na vlastníka (dotýká se produkční větve).

1. PR #8 čeká na review/schválení vlastníka (merge = deploy). Po nasazení ověřit, že při dalším
   deployi nevznikne duplikát. Zvážit obecnější ochranu (leader lock pro celý obchodní loop, ostatní boty).
2. Kontrola duplicit — HOTOVO 13:10: `tools/autopilot/duplicate_trades_check.sql` (9 tabulek, jen SELECT), krok v RUNBOOK.
   Stav 13:10: bestof 1 skupina (známý id 129), ostatní 0. Chybí FLY/V8 tabulky (jiné schéma, FLY má `fly_trade_exclusions`).
3. Combined replay: export ledgeru HOTOVO (draft PR #9 → research/autopilot, `research/combined_selection_replay/trades/`,
   CONSISTENT, 300 legů; nezávisle přepočteno z trades.csv: 24 bloků, 0 neshod — komentář v PR #9). Dál: 1. 12. 2026 spustit NOVÝ běh s `--end 2026-12-01` (stejný protokol + export),
   výsledky přidat jako nový řádek, předchozí nepřepisovat.
4. Forward PAPER evidence: týdně souhrn ELITE V18/V56, Combined, LH-WHALE, LIQUIDITY, Swing
   (počet, P/L, PF); ≥ 30 nových obchodů na strategii před závěrem. Registr: `automation/STRATEGY_REGISTRY.md`.
5. `test_expired_and_future_signals_never_open` prochází jen formálně — přepsat v PR.
6. `render.yaml` neodpovídá službě (`app_v8_ui` vs `app_v8_fly`) — opravit v PR.

## Rozhodnutí vlastníka 2026-11-05 (11:47 SEČ) — priority dalších běhů

- PR #8: připravit bezpečný plán nasazení (HOTOVO, report výše) — **sloučení ani deploy NESCHVÁLENO**.
- Id 129: návrh tabulky výjimek jen ve výzkumné větvi (HOTOVO: draft PR #10 → research/bestof-dedupe-20261105,
  `b7a77af`, CI 25 passed). **Žádné změny produkční DB ani historických obchodů.**
- Priority: (1) vývoj a testování PAPER strategií, hledání prokazatelně ziskových po VŠECH nákladech
  (nezávislá validace mimo vzorek); (2) Combined replay; (3) kontrola BEST-OF (duplicity, statistiky).
- Šetřit limity: neopakovat úspěšné testy bez důvodu; jeden konkrétní úkol na běh, výsledky hned commitnout.
- Blokace 2026-11-05 11:04 UTC: plánovaný běh selhal — **limit využití účtu (usage limit)**. Při dalším
  selhání to nahlásit vlastníkovi a zkrátit běh na kontrolu + jeden malý úkol.

## Čeká na vlastníka

- Draft PR #10 (návrh výjimky id 129) — review; neprovádět bez souhlasu.
- Draft PR #8 (BEST-OF duplicitní zápis) — vlastník 2026-11-05 10:42 UTC: **ZATÍM NESLUČOVAT**; připraven
  plán nasazení v `reports/bestof-duplicate-129-and-pr8-deploy-plan-20261105.md`, čeká na schválení.
- Id 129: vlastník **NEMAZAT ani NEUPRAVOVAT**. Čtecí analýza hotová (týž report): duplicitní zápis
  uzavření id 128 starou instancí 9r8m5 v 09:14:11 při překryvu deploye; `paper_balance` správně,
  chybně jen statistiky (129/−393,31 místo 128/−383,00). Návrh: tabulka `bestof_trade_exclusions`
  (vzor FLY), vratné DELETE. Neprovedeno — čeká na souhlas.
- Draft PR #9 (Combined ledger export, cíl research/autopilot) — review; produkce se nemění.

## Blokace

- Žádné. Render konektor funguje (čtení). Sandbox nemá PyPI ⇒ testy s FastAPI běží v GitHub Actions
  (lokálně jen se stuby).
<!-- /orig -->

## Archiv (jen v `automation/archive/STATE-do-20261116.md`)
| Řádky | Obsah |
|---|---|
| 1–6 | záhlaví a historie „Poslední aktualizace“ běhů do #65 (ř. 3, 21 kB; aktuální stav = CHECKPOINT) |
| 7–25 | ZMĚNA PRODUKCE 2026-11-06 (#25, #26; překonáno live `6a23c58`) |
| 26–78 | Produkce — zápisy běhů #37–#43 |
| 79–94 | Databáze `xrp-bot-db` — historie velikosti a odhad stropu |
| 177–261 | FRONTA v2 R1–R13 (výsledky, výtah aktivních bodů výše) |
| 262–314 | VÝZKUMNÁ FRONTA STRATEGIÍ 2026-11-05 + společný protokol |
