# K3 krok 0b — výsledek a nezávislá kontrola (2026-11-10, autopilot běh #47)

Protokol `PROTOCOL_0B.md` commit `5d8989e` (před daty), kód + 4 testy `68e02b0`, výsledky `e27a02f`
(run 42841025758, 185 HL požadavků, všechny HTTP 200). SHA-256 `step0b_by_symbol.csv`:
`771e9fc983bb57be7018f165dea7c147ab38221b49c8bf023ae41ff64aa26bd1`.

**Verdikt: DATA NO-GO pro výkon** (0/160 symbolů projde, potřeba ≥ 20).
- HL `candleSnapshot` 1h vrací nejvýše ~5 000 svíček bez ohledu na `startTime` (max 5 004, medián 208,4 dne,
  max 208,5 dne < 548). Stránkování dozadu nic dalšího nevrací ⇒ potvrzen očekávaný limit z dodatku 1.
- Binance Vision `markPriceKlines` 1h: měsíční soubory + CHECKSUM za 100 % měsíců okna (medián) — Binance strana není úzkým hrdlem.
- Synchronizace: 100 % HL svíček na celé hodině (±1 min).
- Survivorship: část symbolů má poslední HL svíčku ve 2025 (např. FTM, RDNT, BNT) = delisting na HL; krok 0 bral HL `meta`
  k dnešku, takže tyto by výkonnostní běh musel řešit zvlášť (dodatek 1 bod 3).
- Nezávislý přepočet brány z CSV (samostatný skript, ne `gate()`): 0 projde, shoda s CSV 160/160.

Důsledek podle dodatku 1 bod 1: žádná interpolace z denních close; primární výkonnostní běh K3 nelze provést
z bezplatných veřejných dat. Denní konzervativní odhad smí být jen diagnostika bez kandidátního verdiktu.
Možná cesta bez placených služeb: forward sběr HL hodinových cen od dneška (důkaz dostupnosti až po ≥ 548 dnech) — nedoporučuji jako prioritu.
