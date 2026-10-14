# ELITE — registr experimentů a vyčerpaných dat

Aktuální stav: žádný schválený kandidát pro PAPER; žádné nasazení. Výzkum je
oddělený od ostatních botů na větvi `elite-research-v1`.

| Verze | Rozhodnutí / zjištění | Záznam |
|---|---|---|
| V1 | Zamítnuta, ztrátová všechna roční období; starý simulátor | V1_BACKTEST_RESULT.md |
| V2 | Zamítnuta, ztrátová expanze volatility | V2_BACKTEST_RESULT.md |
| V3 | Zamítnuta, malý zisk posledního bloku nepřebil ostatní ztráty | V3_BACKTEST_RESULT.md |
| V4 | Výsledek přesně zopakován, ztrátová i bez nákladů ve vývoji/validaci | RESEARCH_REPORT_20261013.md |
| V5 | Zisk závisí na trendech; validační blok ztrátový | RESEARCH_REPORT_20261013.md |
| V6 | Nedostatečný vzorek a validační ztráta | RESEARCH_REPORT_20261013.md |
| V7 | Ztrátová všechna období, vysoké náklady/propady | RESEARCH_REPORT_20261013.md |
| V8 | Kladná vývojová bilance, pouze 36 obchodů, nejistá očekávaná hodnota | REPORT_V8_V11_20261014.md |
| V9 | Ztrátový návrat k průměru v bočním trhu | REPORT_V8_V11_20261014.md |
| V10 | Kladná celková bilance závisí na jediném velkém obchodu | REPORT_V8_V11_20261014.md |
| V11 | Kladná vývojová bilance, pouze 22 obchodů, nejistá očekávaná hodnota | REPORT_V8_V11_20261014.md |
| V12 | Hodinová V8, 161 obchodů; ztrátová i bez nákladů | REPORT_V12_V14_20261014.md |
| V13 | Zotavení RSI, ztrátové i bez nákladů | REPORT_V12_V14_20261014.md |
| V14 | Průraz po úzkém rozpětí: hrubý zisk neodolá nákladům | REPORT_V12_V14_20261014.md |
| V15 | Kombinace +47,39 %, ale jen 2/4 kladné bloky a nadlimitní DD | REPORT_V15_V17_20261014.md |
| V16 | Režimová kombinace +23,63 %, jen 2/4 kladné bloky a nadlimitní DD | REPORT_V15_V17_20261014.md |
| V17 | Kombinace +12,15 %, jen 2/4 kladné bloky, koncentrovaný zisk | REPORT_V15_V17_20261014.md |
| V18 | Filtr BTC: +47,18 %, 3/4 kladné bloky; nadlimitní DD a nejistota | REPORT_V18_V20_20261014.md |
| V19 | Relativní síla XRP/BTC: ztrátová souvislá bilance | REPORT_V18_V20_20261014.md |
| V20 | Dohánění BTC: +2,92 %, jen 32 obchodů a 2/4 kladné bloky | REPORT_V18_V20_20261014.md |

| V21 | Posuvný stop V18: +6,62 %, DD 6,94 %, jen 2/4 kladné bloky | REPORT_V21_V23_20261014.md |
| V22 | Výstup při oslabení BTC: +42,81 %, DD 9,60 %, jen 2/4 kladné bloky | REPORT_V21_V23_20261014.md |
| V23 | Kombinace výstupů: +6,06 %, záporný zátěžový test | REPORT_V21_V23_20261014.md |

| V24 | Návrat nad proražené minimum: −0,04%, náklady a zpoždění ruší výhodu | REPORT_V24_V25_20261014.md |
| V25 | Návrat k proraženému maximu: +10,07%, jen2/4 kladné bloky | REPORT_V24_V25_20261014.md |

## Datový registr

- Říjen 2025–září 2026: opakovaně použito V1–V25. Nikdy znovu neoznačovat
  jako nedotčený závěrečný test.
- Duben 2023–září 2026: prohlédnuto při V5–V25; všechna tato data jsou vývojová.
- Březen 2023: kontrola kvality našla mezeru 16 svíček. Data nebyla imputována;
  posun počátku na duben byl zaznamenán před prvními výsledky V5–V7.
- Roky 2022 a 2021: během této série výzkumu neotevřeny, rezervované pro předem
  zmrazené kandidáty podle protokolů. Toto neprokazuje, že je nikdo nikdy dříve
  nepoužil v jiném projektu. Test na minulých letech není dopředná validace.
- Nová budoucí data: nezbytná pro skutečnou prospektivní validaci.

## Co neopakovat

1. Nepřijímat strategii podle jediného kladného souhrnného backtestu.
2. Nezaměňovat úspěšné provedení GitHub workflow za ziskovost strategie.
3. Neodstraňovat náklady, nezvyšovat pozice ani nezmírňovat podmínky kvůli
   nevyhovujícímu výsledku. Levnější skutečné provedení je nutné doložit.
4. Nedávat novému názvu strategie význam nové nezávislé hypotézy; V12 je
   například přenos V8 na jiný časový rámec a V11 odvozenina V5.
5. Pamatovat na selekční zkreslení po nejméně dvaceti pěti zkoušených verzích.
   Uváděné intervaly nejsou opravené na mnohonásobné hledání.
6. Další vstupní pravidla formulovat jako ověřitelnou hypotézu, předem uložit
   parametry a ukázat i neúspěšné pokusy. Neměnit běžící boty.

Úplná evidence je v adresářích `results/20261013`, `results/20261014` a
`results/20261014_v12` a `results/20261014_v15`. Protokoly mají vlastní soubory pro každou sadu.

Pro V18–V20 ověřeny také 42 měsíční archivy BTCUSDT, duben 2023–září 2026, přesně
časově shodné s XRP. Evidence navíc v `results/20261014_v18`. Přidání BTC
nedělá již prohlédnuté XRP období nezávislým testem.

V21–V23: evidence v `results/20261014_v21`. Výstupní varianty V18 snížily
propad, ale nevyřešily stabilitu mezi obdobími. Podmínky nebyly změkčeny.

V24–V25: evidence a diagnostika v `results/20261014_v24`; žádný postup do
rezervovaného testu. V25 přežije stres nákladů, ale neprokazuje stabilitu.
