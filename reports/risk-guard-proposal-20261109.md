# Návrh: společný Risk Guard pro PAPER boty (2026-11-09)

Podnět vlastníka: zadání „senior quant / risk manager“ → vyhodnoceno, vlastník odpověděl „Ano“ na návrh modulu.
Stav: **NÁVRH** — `risk_guard.py` + `test_risk_guard.py` (8 testů). Do žádného bota zatím NEZAPOJENO,
produkce se nemění. Zapojení (fáze 2) jen po výslovném schválení vlastníka.

## Co už boti mají (ověřeno v kódu v8-fly-layer-test)
| bot | riziko/obchod | strop pozice | velikost podle volatility | limity propadu / dne / týdne | kill-switch |
|---|---|---|---|---|---|
| LIQUIDITY v2 (`liquidity_local.py`) | 0,5 % | 35 % equity | ano (stop ze struktury) | **ne** | **ne** |
| LH-WHALE (`lh_whale.py`) | 0,5 % | 35 % | ano | **ne** | **ne** |
| ELITE V18/V56 (`elite_paper.py`) | 0,5 % | 35 % | ano (stop z modelu) | **ne** | **ne** |
| SWING (`swing_paper.py`) | 0,5 %, pool 1,5 % | 35 %, celkem 70 % | ano (2,5×ATR) | **ne** | jen ruční pauza rodin |
| NEWS (`news_paper.py`) | 0,14 % | 35 % | ano (ATR) | **ne** | **ne** |

Chybí tedy přesně vrstva nad strategií: co dělat, když bot prodělává.

## Pravidla Risk Guardu (5 parametrů)
1. **Propad od vrcholu equity bota:** < 5 % plné riziko · 5–10 % poloviční · 10–15 % čtvrtinové ·
   **≥ 15 % KILL** = žádné nové vstupy, dokud vlastník výslovně neresetuje (reset se zapíše: kdo, kdy).
2. **Denní ztráta ≥ 1,5 %** od začátku dne UTC ⇒ do konce dne bez nových vstupů.
3. **Týdenní ztráta ≥ 3 %** od začátku týdne ⇒ do konce týdne bez nových vstupů.
4. **Kill-switch na data:** neplatná / stará cena nebo záložní zdroj ⇒ žádný nový vstup
   (výpadek ELITE 8. 11. ukázal, že přepnutí na Kraken bez hlídání je riziko).
5. **Max. otevřených pozic na bota** (výchozí 1, jak boti mají).

Výstupy (stop, take-profit, trailing) se **nikdy neblokují**. Násobek se aplikuje na `RISK` při výpočtu qty.
Proč tyto hodnoty: při riziku 0,5 %/obchod znamená 1,5 % denně ≈ 3 stopy za den, 3 % týdně ≈ 6 stopů,
15 % propad ≈ 30 stopů po sobě bez zotavení — to už je důkaz, že strategie nefunguje, ne smůla.
Hodnoty jsou stanoveny předem z rizika na obchod, NE optimalizací na historii.

## Fáze 2 (po schválení) — zapojení
Do každého bota 3 řádky: `rg = risk_guard.update(s.get('risk_guard'), equity, peak, now)`,
`ok, mult, why = risk_guard.check_entry(rg, equity, data_ok=valid)`, `qty *= mult` / přeskočit vstup;
stav uložit do `s['risk_guard']`, důvod zobrazit na dashboardu. Regresní testy: vstup zablokován při limitu,
výstup nikdy. Nasazení = ruční deploy vlastníkem.

## Fáze 3 (později) — mezi boty a provedení
- Souhrnný limit rizika na stejný symbol napříč boty (většina botů obchoduje XRPUSDT ⇒ korelace).
- Realističtější skluz: místo pevných 0,02 % podle likvidity symbolu (u altcoinů je 0,02 % málo).
