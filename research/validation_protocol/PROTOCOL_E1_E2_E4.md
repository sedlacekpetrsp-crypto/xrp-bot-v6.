# Protokol ověřovací vrstvy E1 + E2 + E4 (dohoda Claude ↔ ChatGPT, dialog 0201/0202/0206)

Stav: **NAVRŽENO**, zapsáno 2026-11-08 před jakýmkoli během. Výhradně PAPER. Nic se nesloučí ani nenasadí.
Tento protokol nepřidává obchodní hypotézu ⇒ nezvyšuje N v registru. Brány jsou binární (projde/neprojde),
nikdy se nepoužijí k výběru parametrů.

## E1 — sjednocený harness a jeho správnost
Cíl: jeden engine (data + SHA-256, náklady, dělení, metriky, B&H, export) místo 330–574řádkových `run.py`.
Shoda `results.json` se starými běhy (≤ 1e-9) je **nutná, ne postačující** (společná chyba ji projde).

| # | Kontrola | Vstup | Očekávaný výsledek | Failure mode, který chytá |
|---|---|---|---|---|
| G1 | Golden fixture long, 1 obchod | 3 svíčky, ručně spočtený ledger | fill = open další svíčky, fee 0,095 % + skluz 0,02 %/stranu, P/L na 1e-12 | posun fillu, chybná sazba |
| G2 | Golden fixture short + funding | 2 funding okna, znaménko short | short platí kladný funding, přijímá záporný | obrácené znaménko fundingu |
| G3 | Gap přes stop | open pod stopem | fill na open, ne na stopu | optimistický fill |
| G4 | Chybějící svíčka | díra v datech | běh fail-closed (výjimka), ne interpolace | tichá interpolace |
| M1 | Metamorfní: fee ×k | k = 0, 1, 2, 3 | P/L klesá přesně lineárně s k·obrat | náklady mimo obrat |
| M2 | Metamorfní: posun signálu o +1 svíčku | libovolná strategie | ledger = ledger se vstupem o svíčku později (identita) | nekonzistentní indexace |
| M3 | Identita pozic | nulový signál | 0 obchodů, P/L 0, equity konstantní | fantomové obchody |
| R1 | Nezávislý přepočet | `trades.csv` | souhrn z trades.csv = `results.json` | drift metrik |
| R2 | Regrese | R1 Donchian, RSI(2), near-high | ≤ 1e-9 vůči uloženým `results.json` | odchylka refaktoru (neshoda = nález, ne ladění) |

Akceptace E1: G1–G4, M1–M3, R1 zelené v CI (bash pipefail); R2 buď shoda, nebo zdokumentovaný nález.

## E2 — negativní kontroly
**Nulový proces (deklarace předem):** pro danou strategii S a universe U zachovat počet obchodů, rozdělení délek
držení, směr (long/short podíl) a průměrnou expozici; náhodně se mění jen časy vstupů. Jednotka randomizace =
obchod; **blokové přeřazení** po kalendářních blocích 20 dní (mění se pořadí bloků, ne obsah) jako citlivost.
Randomizace se provádí odděleně pro každé U a jen v intervalu, kde jsou data dostupná.

**FPR brána:** R = 1 000 nulových replikací (předem). Počet průchodů branami B ~ Binom(R, p).
Brána platí, když jednostranná horní 95% Clopper–Pearsonova mez p ≤ 0,05 (při R = 1 000 ⇒ cca B ≤ 38).
Selhání = brány jsou měkké ⇒ zpřísnit brány **pro všechny budoucí hypotézy**, ne pro jednu.

**Power (vložená hrana):** syntetické řady (GBM + bloky reálných výnosů) s vloženou hranou se známou dostupností
informace v čase t: slabá / střední / silná (Sharpe hrany 0,5 / 1,0 / 2,0 ročně). Měří se podíl detekcí
z 200 replikací. Předem: detekce silné ≥ 80 %; slabá se jen reportuje.

**Kauzální kanárek (fail-closed v CI):**
1. Invariant `feature_available_at ≤ decision_at < execution_at` pro každý řádek ledgeru.
2. Truncation test (princip freqtrade lookahead-analysis): signál v čase t spočtený z dat do t = signál z plných dat.
3. Úmyslné porušení (feature posunutá o −1 svíčku) **musí shodit CI**; pokud projde, je to chyba testu.

## E4 — sekvenční pravidlo degradace pro forward RSI(2) (zapsáno při 0 uzavřených obchodech)
- Referenční rozdělení: historický OOS RSI(2) z uloženého backtestu (BTC/ETH/XRP/LTC, náklady ×1),
  **blokový bootstrap** po obchodech v blocích 5 obchodů, 10 000 replikací, seed 20261108.
- Kontrolní body: po **15, 30 a 60** uzavřených forward obchodech. Mimo kontrolní body se výsledky
  k rozhodování nepoužívají (2026-12-16 je jen provozní kontrola, ne statistický bod).
- Hranice: pro každý bod k spočítat z bootstrapu rozdělení **průměru k obchodů** (ne 5. percentil jednoho
  obchodu). DEGRADOVÁNO, když forward průměr < q_k, kde q_k je zvoleno tak, aby souhrnná míra falešného
  poplachu přes 3 body byla ≤ 5 % (Bonferroni: q_k = 1,67. percentil). Výpočet q_k proběhne v CI z
  uložených dat a výsledek se commitne **před** 15. forward obchodem.
- DEGRADOVÁNO = statistický verdikt; forward se nevypíná, data zůstávají v evidenci.
- **Kill switch** (oddělený): chybějící/stará data, chyba exekuce, duplicitní obchod ⇒ technický stop, ne verdikt.
- CUSUM se nepoužije, dokud nebude jeho FPR kalibrovaná na stejném nulovém procesu a porovnaná s body 15/30/60.

## E3 (jen stres, ne brána)
Zpoždění +1 svíčka a ×2 náklady se reportují u kandidátů, kteří projdou A/B; nejsou univerzální bránou
(zpoždění může měnit exekuční mechanismus). Velikost bloku bootstrapu se odůvodní autokorelací předem.

## Pořadí implementace
E1 (G/M/R) → E2 kanárek → E2 FPR + power (GitHub Actions, ne sezení) → E4 výpočet q_k před 15. obchodem.

## DODATEK 2026-11-08 (dialog 0217, zapsáno PŘED jakýmkoli výpočtem E1/E2/E4)
Žádný výpočet E1/E2/E4 dosud neproběhl; dodatek jen zpřesňuje, nemění prahy.
- **E2 rozsah tvrzení:** odhad FPR (Clopper–Pearson horní mez) platí jen pro deklarovaný simulační nulový proces
  (zadané univerzum, náklady, permutace/GBM). Není to garance FPR strategie při změně režimu ani náhrada za DSR
  se všemi historickými pokusy N (registr `automation/STRATEGY_REGISTRY.md`).
- **E4 zdroj bloků:** referenční obchody = OOS obchody RSI(2) z uloženého backtestu; přesný soubor a jeho sha256
  se commitnou spolu s q_k (před 15. forward obchodem). Obchody se řadí podle času výstupu.
- **E4 překryv obchodů:** obchody na 4 aktivech se časově překrývají a korelují. Primární bootstrap proto
  převzorkuje **kalendářní bloky 20 dní podle času výstupu** (všechny obchody bloku spolu, jako v E1);
  bloky po 5 obchodech jen jako citlivost. Pokud se q_k obou metod liší o > 25 %, platí přísnější (nižší FPR).
- **E4 násobnost:** Bonferroni kryje jen tři předem dané pohledy 15/30/60. Jakýkoli další pohled k rozhodnutí
  je neohlášený a verdikt z něj je neplatný.
