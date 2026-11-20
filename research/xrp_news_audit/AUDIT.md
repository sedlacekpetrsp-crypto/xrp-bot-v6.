# A6 krok 0 — výsledek datového auditu zpráv o XRP

Run [42680351334](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./actions/runs/42680351334), výsledky `6ac4770`, protokol `625aa88` (před daty). Bez cen a výnosů, N +0. `verify.py`: MATCH (0 neshod přepočtu Z1).

## Zjištění
| Zdroj | Pokrytí | Čas | Jen-XRP titulky |s| ≥ 2 | Brány G1/G2/G3 | Verdikt |
|---|---|---|---|---|---|
| Z1 GDELT GKG (vzorek 243/246 souborů, 363 593 záznamů, PAGE_TITLE 100 %) | 77 XRP titulků; domény hlavně agregátory (biztoc, yahoo, fool, fxstreet), krypto média řídce | DATE crawleru, 15 min | jen **5 zásahů** ve vzorku (2020–24: 2) ⇒ bodový odhad 1 974 / 3 092, ale 95% dolní mez 2020–24 jen **26** | formálně ✓/✓/✓ | **formálně GO, věcně nespolehlivé** |
| Z2 cointelegraph.com (80 888 URL) | XRP URL téměř jen 2026 (2 659), starší archiv v sitemapě chybí | jen `lastmod` | 0 / 134 | ✗/✗/✗ | NO-GO |
| Z2 coindesk.com (13 485 URL; 15 sitemap-indexů timeout) | 152 XRP URL, jen 2024–26 | `publication_date` na minuty | 8 / 3 | ✗/✗/✗ | NO-GO |
| Z2 decrypt.co (116 374 URL) | 2 408 XRP URL 2018–2026, každý kvartál | jen `lastmod` (≠ publikace) | 81 / 46 | ✗/✗/✓ | NO-GO |
| Z3 zpoždění GDELT vs publikace | 0 shodných URL | — | — | nezměřeno | — |

## Verdikt
**DATA NO-GO pro historický backtest A6-S** (titulek ⇒ výnos XRP 15 min–4 h). Z1 prošel bránou G1 jen bodovým odhadem
z 2 zásahů za 5 let (interval 26–5 570); brána v protokolu byla špatně specifikovaná (měla používat dolní mez) —
uvádím to otevřeně a výsledek nepovažuji za GO. Plné stažení GDELT GKG 2020–26 (~245 tis. souborů, řádově TB) je pro
GitHub Actions neproveditelné; GDELT DOC API pokrývá jen ~3 měsíce. Z2 nemá u 2 ze 3 zdrojů čas publikace vůbec.

## Proč NEWS bot nemá obchody (jen čtení kódu `news_paper.py`/`news_signal.py` @ `v8-fly-layer-test` + SELECT stavu)
- Stav v DB 2026-11-09 19:05 UTC: `reason = "Čekám na čerstvou pozitivní zprávu z RSS zdrojů"`, 0 obchodů, `used_headlines` 0 ⇒ nikdy neprošla ani zpravodajská brána.
- Brána `bullish` vyžaduje současně: titulek jen o XRP (bez BTC/ETH/SOL), ≤ 2 h starý, bez slov could/may/if/not/predict/„?“,
  žádný negativní titulek, součet skóre ≥ 4 a (titulek se skóre ≥ 4 nebo 2 zdroje se skóre ≥ 2); potom ještě tržní potvrzení FLY (`news_only`) do 25 s.
- Četnost z dat auditu: jen-XRP titulky se skóre ≥ 4 v sitemapách cointelegraph+decrypt = **12 za 2018–2026** (2025: 7, 2026: 5), část z nich
  jsou spekulativní články („XRP price $25 if ETF approved…“). ⇒ Bot je navržen tak, že se spustí nejvýš několikrát ročně;
  0 obchodů za ~1 měsíc je očekávané chování, ne chyba. Neměnit bez souhlasu vlastníka.

## Co dál (návrh, nic nespuštěno)
1. A6 jako signál: obnovit jen **forward sběrem** titulků s časem prvního spatření (RSS 3 zdrojů, PIT od první chvíle) — vyžaduje
   rozhodnutí o úložišti (výzkumný soubor přes GitHub Actions cron vs. tabulka v DB) ⇒ dotaz ChatGPT/vlastník.
2. A6-F (zprávy jako risk filtr): událostí s velkým dopadem je málo (desítky za roky) ⇒ jen event-study bez backtestu; nízká priorita.
