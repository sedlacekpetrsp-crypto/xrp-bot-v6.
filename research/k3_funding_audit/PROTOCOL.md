# K3 krok 0 — datový audit mezi-burzovního fundingu (PROTOKOL, sepsán PŘED daty)

Dialog 0257 (návrh) ↔ 0258 (ChatGPT: SOUHLAS s krokem 0 jako čistě datovým auditem). Schválení: OWNER_DECISIONS
2026-11-10 „obnovení hledání PAPER strategií … datové audity bez výkonnosti“. Výkonnostní běh K3 NENÍ schválen.

## Co se měří (jen metadata, žádné hodnoty fundingu)
Pro každou burzu V ∈ {binance, bybit, okx, hyperliquid} a symbol s z PIT univerza `listings.csv` (PR #38, 923 USDT-M
perpů Binance vč. delistovaných):
1. Dostupnost zdroje z GitHub runneru (HTTP kód první odpovědi; 403/451 = BLOCKED).
2. Mapování symbolů: Binance `XXXUSDT` → Bybit `XXXUSDT`, OKX `XXX-USDT-SWAP`, Hyperliquid `XXX`
   (`1000XXXUSDT` → HL `kXXX`, OKX `XXX-USDT-SWAP`). Nenamapované = počet, bez ručních oprav.
3. Časové razítko vypořádání: první/poslední, počet, podíl razítek ≤ 60 s od celé hodiny (PIT zarovnání).
4. Interval: nominální interval v bodě = modus rozdílů v klouzavém okně 21 rozdílů (zaokrouhleno na h);
   chybějící vypořádání v mezeře = round(Δ / nominál) − 1; pokrytí = n / (n + chybějící). Počet změn intervalu.
5. Společná historie páru burz (A, B) pro s: překryv [max(first), min(last)], v překryvu pokrytí každé burzy zvlášť.

Zakázáno: rozdělení fundingu, rozdílů, výnosů, korelací; jakékoli obchodní pravidlo. Surová data jdou jen do artefaktu
běhu (ne do repozitáře) pro budoucí předregistrovaný protokol.

## Brána (pevná)
- Kvalifikující symbol: existuje pár burz se společnou historií ≥ 548 dní (18 měsíců) a pokrytím ≥ 95 % na obou.
- **GO pro návrh výkonnostního protokolu**: ≥ 20 kvalifikujících symbolů. Jinak **DATA NO-GO** a K3 končí
  (bez placeného zdroje).
- Reportuje se i varianta „Binance povinně jako jedna noha“ (informativní, brána je výše).

## Známá omezení (před daty)
- OKX veřejné API vrací jen ~3 měsíce historie fundingu ⇒ očekávám, že OKX bránu sám nesplní.
- Bybit/OKX mohou z US runnerů vracet 403 (geo-blokace) ⇒ výsledkem je BLOCKED, ne obcházení přes proxy.
- Hyperliquid perpy od ~05/2023; rate limit ⇒ adaptivní backoff, vlastní job.
- Krok 0 neověřuje náklady, převody kolaterálu ani riziko protistrany (to patří do protokolu, viz 0258).
