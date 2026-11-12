# K3 krok 0 — nezávislá kontrola výsledků (autopilot běh #46, 2026-11-10 11:15 UTC)

Vstup: výsledky `f4f8ca7` (run 42784565575), protokol `9d2290f`, kód `4083c80`. Kontrolováno jen z commitnutých CSV,
bez nového stahování. Žádné hodnoty fundingu ani výnosy se nepočítaly.

| Kontrola | Výsledek |
|---|---|
| Přepočet brány z `pairs_overlap.csv` (days ≥ 548 ∧ cov_a ≥ 0,95 ∧ cov_b ≥ 0,95) | shoda se sloupcem `qualifies` 816/816; **160 kvalifikujících symbolů** (vše pár binance–hyperliquid) ≥ 20 ⇒ **GO** |
| Přepočet `days` z `coverage_by_symbol_venue.csv` (min(last) − max(first)) | 804/816 shoda ±1 den; 12 rozdílů = páry bez překryvu (záporný překryv uložen jako 0), žádný kvalifikující |
| Délka společné historie kvalifikujících | min 555, medián 1 016, max 1 269 dní; ≥ 730 dní: 124; ≥ 1 000 dní: 84 |
| Bybit | 403 u všech 918 dotazů ⇒ BLOCKED (geo), dle protokolu bez obcházení |
| OKX | jen ~92 dní historie (známé omezení API) ⇒ žádný kvalifikující pár |
| Hyperliquid | 214 z 235 coinů namapováno; první data 2023-05-12; 25 symbolů má 1 změnu intervalu a mezeru ~8 h na začátku historie (3 chybějící vypořádání) — pokrytí stále ≥ 0,99 |
| Binance | 918/923 symbolů s daty, poslední vypořádání 2026-10-31 (měsíční archivy Vision); 228 symbolů změnilo interval (8 h → 4 h/1 h) ⇒ výkonnostní protokol musí brát skutečná vypořádání, ne pevných 8 h |

## Závěr
GO pro **návrh** výkonnostního protokolu (jen pár Binance USDT-M × Hyperliquid). Výkonnostní běh **NENÍ schválen**
(OWNER_DECISIONS 2026-11-10: výkon nové hypotézy až po dalším výslovném řádku vlastníka).

## Omezení, která musí řešit výkonnostní protokol
1. Hyperliquid je DEX s kolaterálem USDC, Binance USDT ⇒ riziko USDT/USDC, převody kolaterálu (latence, poplatek), riziko protistrany dvou různých typů.
2. Výsledek P/L závisí i na basis (rozdíl cen perpů mezi burzami) — krok 0 ceny HL nekontroloval ⇒ krok 0b (dostupnost historických denních cen HL pro 160 symbolů) je podmínkou výkonu.
3. Funding HL je hodinový se stropem, Binance 8h/4h/1h — sčítat skutečná vypořádání v čase jejich zveřejnění (PIT).
