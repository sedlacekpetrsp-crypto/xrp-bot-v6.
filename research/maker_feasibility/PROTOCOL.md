# Maker execution feasibility — diagnostický protokol (H0/C), verze 1 ZMRAZENÁ 2026-11-07

Výhradně PAPER, jen čtení dat. **Žádný výkonnostní backtest, žádný retest 190 hypotéz.**
Cíl: zjistit, zda existuje proveditelný nákladový režim výrazně levnější než dosavadní model
(0,095 % poplatek + 0,02 % skluz na stranu ⇒ ~0,23 % round-trip). Výstup je interval, ne bodový odhad.

## Krok 0 — atribuce selhání (rozhoduje, zda má krok 1+ smysl)
Pro každý uzavřený výsledek (RESULTS.md / results.json v PR větvích, seznam v `automation/STRATEGY_REGISTRY.md`)
zapsat do tabulky: hrubý P/L validace = čistý ×1 + náklady ×1 (funding zvlášť), náklady ×1, čistý ×1, a které brány padly.
Hypotéza je **nákladově limitovaná** jen pokud současně:
(a) hrubý P/L validace > 0 a bez top 3 > 0 i před náklady, (b) neselhala DSR, walk-forward ani placebo z jiného důvodu,
(c) při nákladech 0,5× (dolní mez reálného maker režimu, viz krok 2) by prošla A1–A5 kromě nákladových bran — počítáno
pouze lineárně z hotových sloupců, bez nového běhu.
**STOP 0:** pokud nákladově limitovaných hypotéz je 0, krok 1+ se neprovádí; C = ZAMÍTNUTO jako směr.

## Krok 1 — nominální poplatky (bez dat trhu)
Veřejný Binance fee schedule (VIP 0, USDT-M perp i spot, maker/taker, s BNB slevou a bez) s datem stažení a URL.
Pouze tier, který účet reálně má; vyšší tiery jen informačně.

## Krok 2 — spread, hloubka, fill (veřejná data Binance data.vision)
Zdroj: `bookTicker` / `aggTrades` daily zip pro symboly z kroku 0, 3 náhodné týdny předem vylosované seedem 20261107
z období validace (ne final_test). Časová razítka v UTC ms, kontrola monotonie a mezer.
Měřit: medián a 90. percentil relativního spreadu; podíl minut, kdy by limitní příkaz na best bid/ask o velikosti
dle protokolu dané hypotézy byl celý zobchodován do T ∈ {1 min, 15 min} podle aggTrades.
**Konzervativní meze fillu:** dolní = obchodovaný objem na ceně ≥ 2× naše velikost + cena přešla přes level
(trade-through); horní = jakýkoli obchod na naší ceně. Queue position neznáme ⇒ výsledek jen jako interval.

## Krok 3 — adverse selection a nevyplněné příkazy
Pro vyplněné limitní příkazy: mark-out mid ceny za 1 a 15 min (bps proti nám). Pro nevyplněné: náklad dohnání
taker příkazem po T (taker fee + spread + pohyb). Efektivní náklad = p_fill × (maker fee + mark-out)
+ (1 − p_fill) × (taker fee + spread + pohyb).

## Krok 4 — funding a inventář
Jen pro perp hypotézy: funding beze změny proti dosavadnímu modelu (se nenásobí); delší expozice kvůli čekání na fill
se přičte jako riziko (směrodatná odchylka výnosu za T), ne jako výnos.

## Varianty (max. 2, předem)
V1: limit na best price, T = 1 min, pak taker. V2: limit na best price, T = 15 min, pak taker.

## Rozhodnutí
- **PROVEDITELNÉ**: horní mez efektivního round-trip nákladu (konzervativní fill) ≤ 0,5 × 0,23 % u obou variant
  ⇒ návrh na předregistrovaný přepočet *jen* nákladově limitovaných hypotéz z kroku 0 (vyžaduje nový protokol).
- **NEPROVEDITELNÉ**: dolní mez > 0,75 × 0,23 %.
- Jinak, nebo chybí-li data / mezery > 1 % minut: **NEROZHODNUTO** (fail-closed).
Žádný výsledek tohoto protokolu není sám o sobě důkazem ziskovosti strategie.
