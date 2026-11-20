# K11 BINANCE_SPOT_DELIST_DRIFT — výsledek KROKU 0 (datový audit): **DATA NO-GO**

Běh: GitHub Actions run 44678047829, kód `ad93b16` (PR #71), výstupy `12a5a19`. Výnosy NEPOČÍTÁNY, ceny nečteny.
`events.csv` SHA-256 `d8a17fa1…7b15965`, `step0_manifest.json` SHA-256 `c3b64605…d84eeee4` (URL, status a SHA-256 všech 5 845 odpovědí v manifestu).

## Brána §4 (zmrazeno předem)
| Podmínka | Práh | Výsledek |
|---|---|---|
| (a) způsobilé události / nezávislé články | ≥ 60 / ≥ 25 | **0 / 0** (i kdyby PIT byl dokonalý: perp_ok ∧ coverage_ok = **50 / 24** ⇒ stále pod prahem) |
| (b) OOS události (≥ 2025-01-01) | ≥ 20 | 0 (bez PIT 34) |
| (c) podíl pit_unverified | ≤ 30 % | **100 %** (146/146, contradicted 0) |
| úplnost výčtu (dodatek 3 bod 1) | nečitelné ≤ 5 % | **5,13 %** (2/39) |
Citlivost `gate_sensitivity_truncated_intraday_end`: rovněž DATA NO-GO (0 událostí zkráceno).

## Proč (fakta z manifestu)
1. **PIT nelze doložit:** CDX vrátil 144 snímků přes 3 prefixy, v oknech článků 8 unikátních; **0 vykreslených** (SPA bez seznamu
   článků) ⇒ žádné pozorování. Riziko bylo zapsáno předem v dodatku 2 — legitimní negativní výsledek, ne důvod měnit zdroje.
2. **Výčet CMS sahá jen do 2022-02-17** (447 článků, 9 stran, integrita stránkování OK); 2020–2021 API nevrací ⇒ populace menší, než
   předpokládal protokol.
3. Perp + pokrytí (CHECKSUM, funding, ≥ 95 % celého okna): 50 ze 146 tokenových událostí (66 má perp, 16 neprošlo pokrytím).
4. Nečitelné titulky: „COS, **D**, HIGH, MBOX“ (ticker o 1 znaku — omezení regexu `{2,15}`) a „UTK and Support Rebranding…“.
   Oprava parseru by verdikt nezměnila (rozhodují body 1 a 3), proto se po zhlédnutí dat NEOPRAVUJE ani nespouští znovu.
5. Diagnostika knihy (0407): `bookTicker` v den oznámení 2/66, `bookDepth` 59/66.

## Rozhodnutí
Podle §4: **K11 se uzavírá bez výkonu.** Žádné rozšíření na Monitoring Tag / margin / pair_removal jako náhradní populaci,
žádný jiný PIT zdroj ani změna prahů po zhlédnutí dat (poučení A5/K8). Znovuotevření jen novou předregistrací s nezávislým
PIT zdrojem času oznámení (ne po zhlédnutí těchto výsledků vymyšleným). N pro DSR: +0 (výnos netestován).
