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

| V26 | Průraz s objemem: +0,89%, záporný stres; horší než bez filtru | REPORT_V26_V27_20261014.md |
| V27 | Obrat s objemem: −0,88%, pouze37 obchodů | REPORT_V26_V27_20261014.md |

| V28 | Průraz s taker-buy převahou: +14,34%,54 obchodů,2/4 kladné bloky | REPORT_V28_V29_20261014.md |
| V29 | Zotavení přes převahu taker-sell: −7,33%,1/4 kladné bloky | REPORT_V28_V29_20261014.md |

| V30 | Měsíční výběr180d: +10,69%, DD5,79%,2/4 kladné bloky | REPORT_V30_V31_20261014.md |
| V31 | Výběr180d+90d: +7,36%, DD4,16%,51 obchodů a nejistota | REPORT_V30_V31_20261014.md |

| V32 | 15m komprese/průraz: −14,89%, ztráta i při nulových nákladech | REPORT_V32_V33_20261014.md |
| V33 | 15m zotavení v4h trendu: −8,48%, nedostatečná rezerva na náklady | REPORT_V32_V33_20261014.md |

| V34 | Týdenní VWAP reclaim: −11,13%, časté výstupy a náklady | REPORT_V34_V35_20261014.md |
| V35 | Návrat k VWAP: −45,07%, ztráta i bez nákladů ve vývojovém souhrnu | REPORT_V34_V35_20261014.md |

| V36 | V18 OR V28: +51,64%, vyšší DD12,30%,2/4 kladné bloky | REPORT_V36_V37_20261015.md |
| V37 | V18 AND V28: +9,07%, DD4,70%,pouze36 obchodů | REPORT_V36_V37_20261015.md |

## Datový registr

- Říjen 2025–září 2026: opakovaně použito V1–V37. Nikdy znovu neoznačovat
  jako nedotčený závěrečný test.
- Duben 2023–září 2026: prohlédnuto při V5–V37; všechna tato data jsou vývojová.
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
5. Pamatovat na selekční zkreslení po nejméně třiceti sedmi zkoušených verzích.
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

V26–V27: první experiment této série s base-asset volume; evidence a předem
stanovené cenové kontroly v `results/20261014_v26`. Nový vstup neobnovuje OOS.

V28–V29: směrový taker objem a cenové kontroly v `results/20261014_v28`.
Směrový filtr nevyřešil stabilitu; žádný kandidát k rezervovanému testu.

V30–V31: kauzální měsíční volba ze6 pevných strategií,432 uložených skóre
a úplná evidence v `results/20261014_v30`. Kauzalita výběru není nezávislé OOS.

V32–V33: evidence a diagnostika v `results/20261014_v32`. Častější15m vstupy
ani pevný2% cílový odstup nevytvořily přijatelnou strategii.

V34–V35: evidence v `results/20261014_v34`; obě zamítnuty. Následuje
pevně vymezený půlroční audit existujících variant, nikoli další ladění prahů.

## Audit půlroků 15.10.2026

Beze změny strategií V5,V18,V22,V28,V30,V31. Společných6 půlroků říjen2023–
září2026: V18 a V28 mají5/6 kladných, ale nejde o nové brány ani OOS.
V28 má málo obchodů; měsíční výběr V30/V31 stabilitu jednoznačně nezlepšil.
Viz `REPORT_HALFYEAR_20261015.md` a `results/20261015_halfyear`.

V36–V37: evidence `results/20261015_v36`; kombinace původních filtrů nevyřešila
stabilitu. V36 zhoršuje DD, V37 snižuje již malý počet obchodů.
