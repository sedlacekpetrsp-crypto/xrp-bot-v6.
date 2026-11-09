# A3 krok 0 — výsledek datového auditu Binance Vision `metrics` (2026-11-09)

Protokol `efad5ed` (před daty) + dodatek 1 `96e838b` (parser, pravidla beze změny). Běh 42582439134, výsledky `1928ac2`.
Jen pokrytí dat, žádné ceny ani výkonnost. Nezávislý přepočet brány z CSV (`verify.py`): **MATCH**.

## Brána: **GO — jen pro návrh protokolu A3, s denní (ne intradenní) dostupností OI**
| Bod | Výsledek | Práh |
|---|---|---|
| G1 aktiva s pokrytím ≥ 95 % a každým kvartálem ≥ 90 % | **77 / 79** v okně (81 v univerzu, 2 mimo okno: BZRX, LEND) | ≥ 15 |
| G2 nejslabší kvartál | 2026Q2: 60 aktiv ≥ 90 % (2022Q1: 79; pokles = delistingy) | ≥ 15 |
| G3 podíl delistovaných | 27,3 % mezi vyhovujícími vs 26,6 % v univerzu | rozdíl ≤ 15 p. b. |

- Soubory: 124 178 denních archivů, SHA-256 = `.CHECKSUM` 100 %, 2 nestandardní klíče (nepočítány).
- Metrics začínají 2021-12-01 u všech aktiv ⇒ okno 2022–2026 je úplné.
- Nejhorší aktivum: **CVCUSDT 49,0 %** (13 výpadků, nejdelší 16 823 h ≈ 2 roky; nejspíš pozastavení a re-listing pod stejným
  tickerem), **CTKUSDT 77,6 %** (nejdelší výpadek 9 457 h). Ostatní ≥ 98,9 %; typické výpadky 15–39 h.
- Selekční bias: data nezůstávají jen u přeživších (G3).

## Publikační zpoždění — NEPROKAZATELNÉ z Vision
S3 `LastModified` − konec dne (h): 2022 medián 8 606 (min 4 275), 2023 medián 299 (min 5,5), 2024 medián 16 503,
2025 medián 9 542 (min 6,4), 2026 medián 2 038 (min 6,5); podíl ≤ 1 h = 0 % ve všech letech.
⇒ Archiv byl hromadně **přepisován** (mediány měsíce až roky po události), takže `LastModified` neukazuje první
zveřejnění. Nejkratší zpoždění 5,5–6,5 h naznačuje původní publikaci zhruba D+1 ráno UTC, ale prokázat to nejde.

## Důsledky pro protokol A3 (návrh, ke schválení v dialogu)
1. Z Vision **žádné intradenní rozhodování na OI** (dohoda 0239). Rozhodnutí v den D smí použít OI nejvýš do konce D−1
   (konzervativně ≥ 1 den zpoždění); 1h verze A3 jen s vlastním forward sběrem OI v reálném čase.
2. Hodnoty mohly být při přepisu revidovány a revize nejde ověřit ⇒ uvést jako omezení; GO se týká jen pokrytí.
3. Univerzum A3 = zmrazených 81 (77 vyhovujících; CVC a CTK ponechat se skutečnými výpadky, bez imputace).
