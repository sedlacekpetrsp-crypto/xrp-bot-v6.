# Doporučené kroky — kontrola 17. 10. 2026

## Provedené opravy a provozní ověření

- LH Europe již běží na opravě `92e0d0f` z 15. 10. Současné logy ukazují HTTP 200 a `LH-DATA OK WAIT`. Sdílený LH-WHALE má `healthy: true`, PostgreSQL, žádnou datovou ani provozní chybu. `WAIT postgres` je úspěšný scan bez vstupního signálu, nikoli chyba databáze. Starý výpadek sám o sobě není důvod k dalšímu restartu.
- Na sdílenou službu nasazen commit `85336ec`: Whale před odečtením vstupního poplatku ověřuje skutečnou odhadovanou ztrátu na rozšířeném stopu včetně obou poplatků a výstupního skluzu. Kontroluje původní peněžní limit i celkové otevřené riziko podle aktuálních stopů. Nepřepočítává velikost ani cíl; nadlimitní vstup odmítne. Historii ani existující pozice neupravuje.
- Důsledek požadavku zachovat velikost při SL +15 %: pozice původně dimenzovaná přesně na limit se nyní neotevře. Limity se nezvyšují. Poslední FIB pozice s 570,0039 XRP měla odhad rizika 10,1569 proti limitu 9,1782 USDT; nový guard by ji odmítl. Byla již uzavřená, takže nebyla dodatečně změněna. Přijaté kapitálově omezené pozice si zachovávají qty, TP a širší SL. Cenová mezera může odhad ztráty překročit.
- Po nasazení ověřeno: Whale zůstatek 9882,06164798096, sedm obchodů, žádná otevřená pozice ani chyba. FLY/FAST/Lead-Lag/TV mají `status: paused`; VWAP_REVERSION zůstává pozastavená. Jejich účty ani obchodní parametry se neměnily. Žádná nová placená služba.
- 40 cílených testů prošlo. Celý společně spuštěný historický unittest soubor má na původním commitu 19 selhání a jednu importní chybu (chybí pytest), stejně jako změněná verze po aktualizaci očekávání skutečného rizika. Řada starých testů předpokládá dřívější strategie nebo sdílí globální stav. Netvrdíme, že celá historická sada prochází.

## Kontrola skutečných obchodů po nákladech

| Bot | Obchody | Čistý výsledek USDT | Poplatky USDT |
|---|---:|---:|---:|
| FLY | 287 | −821,80 | 871,04 |
| FAST | 104 | −413,46 | 361,56 |
| Lead-Lag | 8 | −50,44 | 51,51 |
| TV trend | 104 | −407,36 | 408,59 |
| TV countertrend | 8 | −29,51 | 18,78 |

FLY počítá kanonické obchody bez tří dříve identifikovaných duplicit. Rozdělení podle setupu/symbolu/směru je v `ledger_cohorts.json`. Jde o historické vybrané exekuce různých verzí, nikoli nezávislý backtest aktuální strategie. FAST i po odečtení vlivu poplatků ztrácí v každém symbolu. U Lead-Lag ani osmi vybraných vstupů nelze prokázat predikční výhodu. TV již má 15m trendový filtr a zakazuje countertrend na hranici vstupu; doporučení jej přidat by duplikovalo existující kód.

## Novější TV replay bez ladění

Protokol a runner byly zmrazeny commitem `773bbe9` před výpočtem výsledků. Jediná varianta: produkční ADX 22, ATR stop 1,5, SL násobek 1,15; poplatek 0,095 % a skluz 0,02 % na stranu. Žádný výběr nejlepší varianty. První pokus skončil před výsledky na nedostatečném warmupu; rozšířen pouze warmup ze dvou na tři dny, bez změny strategie a oken.

| UTC okno, konec výlučný | Obchody | Čistý výsledek | Profit factor |
|---|---:|---:|---:|
| 13. 10. 00:00 – 15. 10. 00:00 | 3 | −26,40 | 0,000 |
| 15. 10. 00:00 – 17. 10. 05:00 | 3 | −10,70 | 0,070 |
| Druhé okno, dvojnásobný skluz | 3 | −11,22 | 0,067 |

Obě okna používají samostatný účet 10000; klíč `development` ve výsledcích je pouze původní název výstupu, zde se nic neladilo. Minutová aproximace: SL před TP při kolizi, stop gap za open, ochrana zisku podle close, drawdown podle uzavřeného zůstatku. Chybí intraminutové pořadí a živé sdílení kapitálu. Novější období je mimo původní TV výzkum z 12. 10., ale trh už byl pozorován v provozních reportech; nejde o dokonale nedotčený holdout. Šest obchodů neposkytuje statistické ověření. Numerická brána neprošla a TV se neobnovuje.

Reprodukce: `python research/recommendations_20261017/download.py DATA_DIR`, následně `python research/recommendations_20261017/run.py DATA_DIR/XRPUSDC_1m.json`. SHA a časové meze jsou v `data_manifest.json`; surová tržní data se znovu stáhnou z uvedeného API.

## FIB a VWAP evidence

Archivováno 597 odlišných, časově se překrývajících kandidátů: 76 FIB, 520 VWAP reversion, jeden reclaim. Kompletní snapshot je v `candidate_snapshot.json.gz`, hash a čas odběru v manifestu. Reprodukce souhrnu: `python research/recommendations_20261017/summarize_candidates.py`.

- FIB průměrný směrový pohyb minus odhad nákladů: 15 minut −0,240 %, 60 minut −0,188 %, 240 minut −0,204 %; jde o 76/75/73 včasných pozorování.
- VWAP reversion: −0,198 %, −0,225 %, +0,046 %. U posledního horizontu je medián −0,060 %; samotný kladný průměr nestačí. Chybějící včasná pozorování nejsou doplňována ani počítána jako výhra.
- Tato čísla nejsou PnL strategie: nezahrnují cestu SL/TP, podmínky vstupu ani nezávislé obchody. Žádný nový RSI/MTF filtr nebyl na základě těchto výsledků povýšen do obchodování. Stávající sběr evidence dál běží.

## Co nelze poctivě označit za dokončený backtest

Plný nezávislý replay aktuálního FLY/FAST a predikční ověření Lead-Lag zůstávají omezené dostupností dat. FLY/FAST vyžadují historický spread, hloubku order booku a časované signály/news včetně stavů bez vstupu. Tabulka FLY signálů tyto vstupy neobsahuje. Lead-Lag má pouze osm vybraných signálových řádků pro osm minut, nikoli souvislou historii kandidátů a zamítnutí; doloženo v `leadlag_signal_coverage.json`. Nelze nahradit chybějící book optimistickou konstantou a výsledek vydávat za validaci.

Podmínka dalšího ověření: souvislá synchronizovaná historie BTC/ETH/XRP a příslušných obchodovaných trhů, obou stran booku/spreadu, časovaných zpráv a všech rozhodnutí, poté zmrazený chronologický replay s poplatky, skluzem a následnou prospektivní PAPER vzorkou. Do té doby se žádná pozastavená strategie nespouští. Ani dokončené opravy nezaručují ziskovost.
