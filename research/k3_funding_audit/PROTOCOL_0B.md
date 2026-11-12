# K3 krok 0b — hodinová datová brána (jen časová razítka, bez hodnot)

Commit PŘED daty, 2026-11-10 ~15:20 UTC (autopilot běh #47). Plní dodatek 1 bod 1 `PROTOCOL_PERF_DRAFT.md`.
Výhradně PAPER, veřejná bezplatná API přes GitHub Actions, žádné secrets, žádný requester-pays S3, žádná výkonnost.

## Co se měří
Pro 160 symbolů s `pair=binance-hyperliquid, qualifies=True` z `pairs_overlap.csv` (krok 0):
1. **HL hodinová cena:** `POST api.hyperliquid.xyz/info {"type":"candleSnapshot","req":{"coin","interval":"1h","startTime","endTime"}}`
   stránkováno dopředu od `startTime = now − 1100 dní`. Zaznamená se jen `t` každé svíčky (nikoli o/h/l/c/v).
   Výstup: nejstarší dostupná svíčka, počet, pokrytí hodin v okně [nejstarší, now].
2. **Binance hodinová mark cena:** Binance Vision `data/futures/um/monthly/markPriceKlines/<SYM>/1h/` — jen existence
   měsíčních souborů (HEAD na `.zip` a `.zip.CHECKSUM`) za měsíce okna; obsah se nestahuje.
3. **Synchronizace ±1 min:** podíl HL svíček s `t mod 1 h ≤ 60 s` (HL funding je hodinový; Binance funding z kroku 0).

## Brána (předem daná, beze změny po datech)
Symbol projde, když HL 1h pokrytí ≥ 95 % na ≥ 548 dnech souvislé historie končící nejdéle 2 dny před během
A Binance markPriceKlines 1h má soubory za ≥ 95 % měsíců téhož okna A on-hour podíl ≥ 99 %.
**GO** při ≥ 20 symbolech, jinak **DATA NO-GO pro výkon** (žádná interpolace z denních close).
Očekávání předem: NO-GO — HL `candleSnapshot` vrací jen posledních ~5 000 svíček (1h ≈ 208 dní).

## Výstupy
`step0b_by_symbol.csv`, `step0b_summary.json`, `step0b_summary.txt` (commit workflowu), nezávislý přepočet brány
z CSV v `AUDIT_0B.md`. Registr: řádek K3-0b, N beze změny (datový audit, žádná varianta výkonu).
