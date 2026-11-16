# LH-WHALE / Issue #56 — diagnostika 13. 11. 2026

## Verdikt
V kontrolovaném stavu bot čeká na platný setup. Nebyla prokázána chyba, která by způsobovala nulu obchodů. **Nejde o opravu obchodní logiky**: PR doplňuje chybějící diagnostiku rozhodnutí, bez změny prahů, risku, časování, deduplikace, stopů či futures pravidel. Není nasazen. Nezávislá kontrola Claudem je vyžádána, nikoli dokončena.

## Navázání na existující práci
Issue #56 a jeho prázdné komentáře; všechny otevřené PR (žádný existující LH-WHALE fix); dialog 0268, 0269, 0273, 0306, 0323 a 0325. WAIT postgres není chyba DB. Historie: `fe9680b` OKX fallback (33 tehdy uváděných testů), `a1b9497` reset epochy, `e64c6c4` Risk Guard, live merge `6a23c584afdf5e4b9cda0ad55da6a6d0c6091057` (264 testů uváděných v merge zprávě). Render poslední live deploy `dep-dbp0cp142hec73fo1srg` odpovídá právě této základně.

## Read-only provozní důkazy
- Správný bot: `/lh-whale/status` na `https://xrp-fly-whale-24-7.onrender.com`, nikoli LIQUIDITY_HUNTER_V2.
- SQL odečty: last_cycle_at 14:21:29.661 a 14:26:09.881 UTC; stav se aktualizuje. Aktuální epocha: 0 uzavřených, žádná pozice, balance/equity 10000; aktivace 6.11., seen 6.11.; cooldown z října. Guard: nulový drawdown, žádný kill. Viz `postgres_readonly.json` a `runtime_status.json`.
- V `lh_whale_trades` zůstávají **2 starší uzavřené obchody**, poslední 24.10.2026 09:03:13.580 UTC. Aktuální nula není celoživotní počet; reset historie nesmazal.
- HTTP snapshot 14:26:14.998 UTC: PAPER, running/healthy, OKX available, WAIT bez setupu, žádný data_error/last_error. Futures ilustrativně LONG 2/3; bez setupu se v původním kódu vyhodnocuje LONG, proto tento údaj není zamítnutý SHORT obchod.
- Vrácená stránka Render logů 14:15:55–14:21:01 UTC obsahuje opakovaný WAIT; `hasMore=true`. Netvrdíme, že šlo o úplný audit všech logů nebo nepřetržité zdraví.

## Pevné historické diagnostické okno (bez výkonového backtestu)
12.11.2026 14:00 UTC < uzavření svíčky <= 13.11.2026 14:00 UTC, tj. 15:00–15:00 SEČ.
Před stažením definováno v `PROTOCOL.md`. Veřejná spot data Binance, uložená v `candles.json` se SHA-256; pouze uzavřené svíčky, ověřena kontinuita, OHLC a čerstvost. Maximum 250 předchozích uzavřených svíček na TF; skutečný API snapshot může obsahovat i otevřenou svíčku, kterou runtime vyloučí. Jde o rekonstrukci setupů z historických OHLC, nikoli přesný replay tehdejšího příjmu API.

| Kumulativní brána | Počet |
|---|---:|
| Validní 5m svíčky | 288 |
| Sweep + reclaim | 21 |
| Souhlas 15m a 1h trendu ve směru sweepu | 1 |
| Navíc volume >= 1.05 | 0 |
| Platný setup | 0 |

267 bez sweep/reclaim, 20 nesouhlas trendu, 1 nedostatečný objem. Původní a nový signal generator daly totožný výsledek na všech 288 vyhodnoceních.
**Historické futures 3/3, jejich dostupnost v okamžiku signálu, risk/time funnel ani skutečné vstupy nelze z dochovaných dat kompletně rekonstruovat**; jsou UNKNOWN, ne domyšlené nuly. Žádný výpočet PnL ani ladění parametrů. Toto okno samo nevysvětluje každý cyklus od 6.11.

## Časové podmínky, futures, risk a ukládání
- `analyze` používá čas **uzavření** 5m svíčky (`row[6]+1`), nikoli její otevření. Podmínka 0–120 s tedy není v rozporu s 5m periodou. Testy ověřují přesně 0, 120000 a 120001 ms i budoucí timestamp.
- Aktivace blokuje pouze svíčky uzavřené před zapnutím/epochou; `seen` se u WAIT neposouvá, futures lze znovu zkusit. Potvrzený signál se i při odmítnutí označí seen — existující konzervativní chování zůstává zachováno. Cooldown, stop distance a risk brány mají explicitní důvody.
- Binance 403/451 spouští existující 15min backoff a kompletní OKX fallback. Žádné míchání poskytovatelů, žádné povolení zastaralých/chybějících futures; existující testy OKX i PIT prošly.
- `tick` zamyká řádek a ukládá pozici do state; řádek trades vzniká **při uzavření**, nikoli při vstupu. Je testován vstup → uzavření → deduplikace a rollback při selhání zápisu. Integrace používá in-memory transakční SQL double + mock HTTP, **nikoli skutečný PostgreSQL server**; produkční DB byla jen čtena.

## Změny
- `lh_sweep.py`: volitelné diagnostické hodnoty z týchž výpočtů jako skutečný setup.
- `lh_whale.py`: reason_code, explicitní směr futures diagnostiky, poslední rozhodnutí vstupu + uchování původního důvodu i po already_seen, strukturované logy po úspěšném ticku.
- `lh_whale_dashboard.py`: důvod analýzy a exekuce, čas a podmínky setupu; běžící cyklus není slib obchodovatelnosti.
- Diagnostika se přenáší v existujícím JSON state; žádná migrace schématu, žádné produkční zápisy v této práci. Větší logy a JSON jsou drobný provozní náklad, který patří do review před případným nasazením.

## Skutečně spuštěné testy
Python 3.12, pytest 9.2.0, pytest-asyncio 1.5.0. `tests.txt` je výstup konečného běhu.
- Cílená sada: **52 passed** (17 nových test cases + 35 existujících).
- Celý repozitář: **281 passed, 38 subtests passed**, 49 deprecation warnings, bez selhání.
- První širší běh narazil na chybějící lokální pytest-asyncio; doplněna pouze testovací závislost prostředí a opakováno. Nový worker test měl závislost na SOCKS prostředí, odstraněna explicitním MockTransport. Produkční závislosti se neměnily.
- `git diff --check` prošel.

Reprodukce:
```sh
python -m pytest -q --disable-warnings
python research/lh_whale_issue56/funnel.py research/lh_whale_issue56/candles.json
```

## Zbývá
Nezávislé review Claudem prostřednictvím `dialog/claude-chatgpt`. Žádný merge, deploy, restart, změna produkční konfigurace/DB ani LIVE. Nasazení by vyžadovalo další výslovné schválení vlastníka. Issue neuzavíráme před review; netvrdíme, že nenasazená diagnostika už běží v produkci.
