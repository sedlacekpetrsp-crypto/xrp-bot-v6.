# K8 — měsíční expirace opcí Deribit (BTC) — KROK 0: datový audit

Stav: NAVRŽENO (autopilot běh #52, 2026-11-11 11:20 UTC). Commitnuto PŘED stažením jakýchkoli dat.
Spuštění kroku 0 až po souhlasu ChatGPT v dialogu (HUNT-10). Výhradně PAPER, v kroku 0 se NEPOČÍTAJÍ výnosy.

## Hypotéza (kontext, v kroku 0 se NEMĚŘÍ)
Deribit (dominantní trh BTC opcí) vypořádává měsíční a čtvrtletní expirace poslední pátek v měsíci v 08:00 UTC;
týdenní expirace každý pátek 08:00 UTC. Před velkou expirací drží dealeři delta-hedge podle gamma pozice
(„pinning“), po expiraci se hedge rozpouští. Literatura u akcií: OPEX efekty (pinning, změna výnosu a volatility
kolem expirace). Kandidátní směrový efekt pro perp: rozdíl výnosu BTC v pevném okně kolem MĚSÍČNÍ expirace oproti
stejnému oknu kolem ostatních pátků (jen týdenní expirace). Termíny jsou mechanické ⇒ PIT z definice.
Novelty: grep `expiry/opex/max pain/friday/pátek/weekday` v registru, inventáři 20261105 a IDEAS = 0 (0257 §2);
dřívější Deribit práce (`btc_variance_risk_premium` DVOL, `btc_option_skew_risk_on`) = úroveň vol/skew, ne kalendář
expirací. Nejbližší rodina: TURN_OF_MONTH (PR #12, zamítnuto) — poslední pátek leží často v okně TOM ⇒ v kroku 1
povinná kontrola překryvu (viz níže).

## Krok 0 — co se audituje (jen data)
1. Seznam expirovaných BTC opcí z Deribit public API `public/get_instruments?currency=BTC&kind=option&expired=true`
   (přes GitHub Actions, SHA-256 každé odpovědi). Pro každou expiraci: `expiration_timestamp`, nejstarší
   `creation_timestamp` instrumentu s touto expirací, počet instrumentů.
2. Klasifikace: MĚSÍČNÍ = poslední pátek měsíce 08:00 UTC; KONTROLNÍ = ostatní pátky 08:00 UTC s týdenní expirací.
   Odchylky (jiný den/čas, chybějící expirace) vypsat, nikdy neimputovat.
3. PIT: měsíční expirace je způsobilá jen pokud nejstarší instrument vznikl ≥ 7 dní před expirací.
4. Pokrytí cen: Binance Vision USDT-M `BTCUSDT` 1h klines (CHECKSUM) v okně ±72 h kolem každé expirace
   (měsíční i kontrolní); událost se počítá jen při 100 % svíček. Funding (Binance Vision fundingRate) — jen pokrytí.
5. Diagnostika (ne brána): podíl měsíčních expirací, jejichž okno −72 h…+72 h se překrývá s TOM oknem PR #12.

## Brána GO (jen pro návrh výkonnostního protokolu)
- ≥ 60 způsobilých měsíčních expirací (PIT + 100 % pokrytí) a ≥ 2 kontrolní pátky na každou z nich v témže
  kalendářním kvartálu;
- chronologické dělení 50/25/25 % ⇒ závěrečný úsek ≥ 15 měsíčních expirací;
- 0 chyb SHA-256 / CHECKSUM. Pokud API `expired=true` nevrací plnou historii (doloženo nejstarší expirací),
  rozhoduje jen to, co vrátí — žádné doplnění z neověřených zdrojů.
Nesplněno ⇒ DATA NO-GO, K8 uzavřít bez výkonu.

## Výkonnostní krok (až po GO, nové oponentuře a řádku vlastníka „SCHVÁLENO: výkonnost K8“) — jen NÁVRH
Jediný primární endpoint předem (volba v oponentuře): D = čistý výnos long/short BTC perp v okně kolem měsíční
expirace − průměr stejného okna kolem kontrolních pátků téhož kvartálu (kontrola dne v týdnu i hodiny zabudovaná).
Náklady ×1/×2/×3 + funding, bootstrap přes události, DSR s N z registru, TOM jako předem zapsaná kovariáta.
Hrubá hrana musí v ladění dosáhnout ≥ 3× náklad ×1, jinak STOP. Závěrečný úsek smí jen zamítnout.
