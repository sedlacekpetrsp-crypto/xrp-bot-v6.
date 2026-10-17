# Prospektivní evidence FLY / FAST / Lead-Lag

Účel: odstranit dosavadní chybějící vstupní data pro další ověření. Modul `research_market_evidence.py` sbírá data na existující sdílené službě. Nevolá obchodní cykly, vstupy ani výstupy; nemění stav botů. Všechny dosavadní pauzy zůstávají v platnosti.

## Pevně stanovený protokol

- Jeden vzorek za 60 sekund, nejvýše 15 veřejných požadavků na vzorek; sdílená ochrana poskytovatele, nejvýše dvě souběžná volání a 25 sekund na celý sběr. Žádné retry obcházející backoff.
- XRPUSDC / ETHUSDC / SOLUSDC: okna 1m a 5m po 250 svíčkách, 20 úrovní bid/ask, poslední dostupná cena. BTCUSDC 1m pro kontext FLY; BTCUSDT / ETHUSDT 1m pro Lead-Lag. Měny ani zdroje se tiše nezaměňují.
- Zprávy jsou snímkem stávající cache v okamžiku sběru, nikoli dnešními zprávami připsanými zpětně minulosti. Neukládají se přístupové údaje; konfigurace má explicitní seznam povolených položek.
- U každého vstupu jsou časy požadavku a přijetí, poskytovatel, maximální cache stáří a nezměněná normalizovaná odpověď. Sekvenční ID knihy není vydáváno za čas burzovní události. U poslední ceny není znám přesný burzovní čas.
- Kontrolují se konečné kladné ceny a objemy knihy, pořadí a nekřížení knihy, OHLCV, zarovnání, mezery, stáří a potřebná délka svíček. Chyba nebo chybějící data zůstávají explicitní; nedoplňují se neutrální knihou ani budoucí cenou.
- Úplný vzorek vyžaduje všechny vstupy, jeden zdroj, sběr do 20 sekund, dostupný stav zpráv a výpočet všech signálových filtrů bez chyby. I neúplné vzorky se uchovávají s příznaky a chybami.
- FLY/FAST/Lead-Lag se počítají v oddělených instancích modulů se stejným zdrojovým kódem. Dostanou pouze zachycená data a čisté indikátory. Nemají přístup k databázovému URL, obchodním callbackům, živým cenám ani sdíleným stavům. Archivují se LONG/SHORT i WAIT a důvody odmítnutí.
- Jde o **signálové filtry**, nikoli simulované obchody. Nevyhodnocuje se exekuce, velikost pozice, recovery režim, portfolio ani PnL. FLY setup-health kontext je kopie produkční historie zmrazená na začátku běhu; je součástí archivu. Nejde o nový nezávislý PAPER účet.
- Samostatné tabulky `research_market_runs` a `research_market_samples`, gzip a SHA-256 pro každý vzorek; hash zdrojů a přesná konfigurace pro každý běh. Jeden záznam na minutový bucket i při překryvu deployů. Produkční obchodní tabulky se nepřepisují.
- Pevný strop 128 MiB fyzické velikosti tabulky vzorků, nejvýše 256 KiB na jeden komprimovaný vzorek. Po dosažení stropu se sběr zastaví a status hlásí `archive_full`. Historie se automaticky nemaže. Žádná nová placená služba. Rozsah archivu lze později vyexportovat přes oprávněný přístup k databázi.

Stav: `/research/market-evidence/status`. Zobrazuje čas posledního uložení, počet a velikost vzorků, jejich kvalitu a poslední signálové filtry; neoznačuje bota za ziskového.

## Limity dalšího testu

Minutové snímky nejsou ticková historie ani úplný proud změn knihy. Nelze z nich určit intraminutové pořadí stopu a cíle nebo přesný okamžik ARMED vstupu. Dodatečné historické svíčky neobnoví chybějící knihu, zprávy nebo události. Smíšené poskytovatele, chybějící záznamy a příliš pomalé sběry je nutné vyloučit z validního synchronizovaného replaye.

Teprve po získání souvislého vzorku lze zmrazit následný exekuční replay a testovat výsledky po poplatcích a skluzu. Z tohoto sběru neplyne automatické spuštění obchodování, výběr parametrů podle výsledku ani potvrzení ziskovosti. Porovnání dopadu dodatečného sběru na provozní zdraví služby patří k ověření nasazení.

Ověření implementace: `python -m unittest test_research_market_evidence` kontroluje izolaci živých stavů, chybějící data, neplatné knihy/svíčky, omezený seznam požadavků, nezveřejnění tajných údajů, gzip roundtrip, deduplikaci a zastavení před zápisem při plném archivu.
