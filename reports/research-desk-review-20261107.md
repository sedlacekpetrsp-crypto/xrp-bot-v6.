# Technické hodnocení: „AI Research Desk“ (Veles) vs. náš výzkumný systém — 2026-11-07

Zadání: ChatGPT → Claude (vlastník předal 2026-11-07 13:34 SEČ). Výhradně PAPER, nic se nenasazuje,
nic se neslučuje. Tento dokument je návrh; žádný z experimentů zatím neběžel.

## 0. Omezení zdroje
Původní příspěvek (x.com/velesxbt/status/2110731912176095700) se nepodařilo načíst — X blokuje
automatické čtení (robots). Kopie na zrcadlech jsem záměrně nepoužil. Hodnocení proto **nevychází
z tvrzení článku**, ale z bodů zadání (stresové testy, walk-forward, evidence hypotéz, sledování
degradace, QuantGPT/MCP), které porovnávám s tím, co je doložitelně v repozitáři. Pokud vlastník
pošle text článku, doplním konkrétní srovnání.

## 1. Co už máme (doloženo v repozitáři)
| Funkce | Kde | Stav |
|---|---|---|
| Příjem hypotéz se šablonou | `automation/IDEAS.md` | funguje |
| Předregistrace protokolu před daty | `research/<x>/PROTOCOL.md`, commit před kódem | funguje (R-série) |
| Evidence všech testů + počet variant N | `automation/STRATEGY_REGISTRY.md`, `tools/research/variant_count.py` (PR #34) | funguje, ručně psaný markdown |
| Korekce na vícenásobné testování | Deflated Sharpe `tools/research/deflated_sharpe.py` (PR R2) | existuje, **ale není v research/autopilot** (kopíruje se do každé větve) |
| Citlivost na náklady ×1/×2/×3 | každý `run.py` | funguje |
| Chronologické dělení + srovnání s B&H | každý `run.py` | funguje |
| Sousední parametry + walk-forward 4 okna | rámec v2 §2 | definováno; implementováno jen v `bab_beta/run.py` (ostatní padly dřív) |
| Nezávislý přepočet souhrnů z trades.csv | každý běh | funguje |
| Forward PAPER | `research/forward/rsi2_pullback/` | běží od 2026-11-07 |
| Nezávislý oponent | ChatGPT přes `dialog/` + evidence gate (`37d176a`) | funguje |
| Atribuce selhání (náklady vs. hrana) | PR #36 | hotovo: 0/16 limitováno náklady |

Závěr: jádro, které „research desk“ přístupy obvykle slibují (registr hypotéz, předregistrace,
walk-forward, korekce na data-mining, forward test), **už máme a je přísnější než běžné návody**
(DSR s N z gitu, opotřebovaný holdout se nepočítá jako důkaz).

## 2. Skutečné nedostatky (ověřené, ne domnělé)
1. **Roztříštěné nástroje.** Každá hypotéza má vlastní engine (`run.py` 330–574 řádků: načtení dat,
   náklady, dělení, metriky). 25 výzkumných PR do `research/autopilot` je otevřených, 0 sloučených;
   DSR nástroj existuje v ≥ 4 kopiích. Riziko: tichý rozdíl v implementaci nákladů nebo metrik mezi
   hypotézami ⇒ nesrovnatelné výsledky a chybné N/DSR.
2. **Chybí negativní kontroly.** Nemáme test, že pipeline *nenajde* hranu tam, kde žádná není
   (náhodné vstupy), a *najde* ji tam, kde je vložená. Bez toho nevíme, jak často by náš proces
   sám vyrobil falešný úspěch.
3. **Chybí stresové testy nad rámec nákladů:** zpoždění exekuce o 1 svíčku, block-bootstrap rozdělení
   max. propadu, rozpad podle režimu trhu.
4. **Forward PAPER nemá předregistrované pravidlo degradace.** Dnes jen „≥ 60 dní a zisk ×2“. Chybí
   srovnání s očekávaným rozdělením z backtestu a pravidlo předčasného ukončení.
5. **Produkční PAPER boty nemají průběžné sledování degradace** — audit 2026-11-06 byl jednorázový.
6. **Registr je jen ručně psaný markdown** — žádná kontrola, že každý `results.json` má řádek a že
   N sedí s `variant_count.py`.

## 3. QuantGPT a MCP — měřitelná výhoda?
- **MCP** je protokol pro připojení nástrojů, ne validační metoda. Už ho používáme (Render, GitHub).
  Samo o sobě nesnižuje riziko falešných strategií.
- **Backtestovací MCP servery / „QuantGPT“ nástroje třetích stran:** neprůhledný engine, neznámý
  model nákladů a skluzu, vlastní zdroje dat, často placené, nereprodukovatelné v našem CI. Pod názvem
  QuantGPT existuje víc různých produktů a nenašel jsem žádné nezávislé ověření jejich výsledků.
  **Verdikt: bez měřitelné výhody, nezavádět.** (Navíc pravidlo „žádné nové placené služby“.)
- Jediné legitimní využití externího enginu: **křížová kontrola** (stejná strategie, stejná data,
  dva enginy ⇒ shoda metrik). Kandidát: open-source QuantConnect LEAN v GitHub Actions. Priorita nízká,
  dokud nemáme strategii, která projde branami.

## 4. Návrh experimentů (priorita, přínos, ověření)
Pořadí respektuje dohodu C → B → E → A → D; nic z toho nepřidává novou obchodní hypotézu, takže
nezvyšuje N (diagnostika nevybírá mezi variantami).

| # | Priorita | Experiment | Ověřitelný přínos / kritérium úspěchu |
|---|---|---|---|
| E1 | vysoká | **Sjednocený harness** `tools/research/harness.py` (data + SHA-256, náklady, dělení, metriky, B&H, export, přepočet) + sloučení DSR a `variant_count` do research/autopilot | „Zlaté testy“: harness znovu vyrobí `results.json` R1 Donchian, RSI(2) a near-high se shodou ≤ 1e-9. Neshoda = nalezená chyba v dosavadních výsledcích. |
| E2 | vysoká | **Negativní kontroly**: (a) 1 000 strategií s náhodnými vstupy a stejným počtem a délkou obchodů ⇒ empirické rozdělení Sharpe; (b) syntetická řada s vloženou hranou; (c) „look-ahead kanárek“ — signál posunutý o −1 den | (a) míra „projde branami“ u náhodných ≤ 5 %, jinak jsou brány měkké; (b) harness hranu najde; (c) test v CI musí kanárka zachytit. Každý budoucí kandidát dostane permutační p-hodnotu. |
| E3 | střední | **Stresová sada** jen pro strategie, které projdou A/B: zpoždění +1 svíčka, block-bootstrap (blok 20 dní, 2 000×) max. DD a zisku, rozpad bull/bear podle B&H | Kandidát musí mít 5. percentil zisku ×2 > 0 a zůstat kladný při zpoždění +1. Jasné, předem dané číslo. |
| E4 | střední | **Předregistrované pravidlo degradace pro forward RSI(2)** — zapsat *teď*, před 2026-12-16: očekávaný výnos na obchod z backtestu (BTC/ETH/XRP/LTC), jednostranný test / CUSUM, ukončit „degradováno“, když po ≥ 15 obchodech je průměr pod 5. percentilem backtestu | Brání posouvání cílů po zhlédnutí dat. Zápis musí mít commit s datem před daty. |
| E5 | nízká | **Týdenní monitor produkčních PAPER botů** (jen čtení DB): klouzavý P/L, počet obchodů, odchylka od historie; jen report | Odchylka se ukáže do týdne místo při dalším ručním auditu. Bez zápisu do produkční DB. |
| E6 | nízká | **Strojový registr** `registry.jsonl` + CI kontrola (každý `results.json` má řádek, N = `variant_count`) | CI selže při chybějícím záznamu; nelze tiše vynechat neúspěch. |
| — | odloženo | PBO / CSCV (Bailey a kol. 2017) | Smysl má u mřížek ≫ 4 variant; u nás max. 4 ⇒ DSR stačí. |
| — | odloženo | Křížová kontrola s LEAN | Až bude kandidát. |

## 5. Rizika
- **Refaktor do harnessu může zavléct chybu** ⇒ zlaté testy (E1) jsou podmínka, starý `run.py` se nemaže.
- **Stresové a permutační testy použité k výběru varianty by zvýšily N** ⇒ pouze jako brána
  (projde/neprojde), nikdy k ladění parametrů.
- **Limity běhů:** E2 (1 000 náhodných strategií) poběží v GitHub Actions, ne v sezení.
- **Sloučení do research/autopilot** (E1) je výzkumná větev, produkce se nedotkne; přesto ho jako
  změnu sdíleného základu předkládám vlastníkovi.

## 6. Doporučení
Žádnou novou infrastrukturu ani externí službu nezavádět. Udělat E1 → E2 → E4 (E4 má termín:
před 2026-12-16). E3 až pro kandidáta, E5/E6 jako údržba. QuantGPT/MCP: nezavádět.
