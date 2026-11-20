# A5 SPOT-LISTING DRIFT — výsledek: DATA NO-GO (PAPER výzkum)

Protokol `1b16021` (před kódem a daty), kód + 23 syntetických testů `852c518`, běh Actions
[42606904512](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./actions/runs/42606904512), výstup `2b55187`.

- Binance Vision: 3 767 spot symbolů, 473 USDT-M perpů (bez recyklovaných tickerů) má spot protějšek.
- Platné události (perp obchodovatelný ≥ 7 dní před prvním spot dnem, S 2020-02-01 … 2026-09-30): **55**
  (2023: 2, 2024: 5, 2025: 33, 2026: 15) — seznam v `events.csv`.
- Pojistka protokolu: < 60 událostí ⇒ **STOP bez metrik výkonu**. Žádné ceny perpů ani výnosy nebyly staženy ani spočteny.
- Důsledek: hypotézu z veřejné historie nelze poctivě rozdělit na ladění/validaci/test (87 % událostí v 2025–26,
  tj. v režimově známém období). Bez dodatku, bez snížení prahu (post-hoc). Případné obnovení jen jako forward
  sběr událostí po 2026-11-09 s novou předregistrací.
- N pro DSR: varianty se nespustily, ale hypotéza byla předregistrována se 4 variantami ⇒ konzervativně N = 218.
