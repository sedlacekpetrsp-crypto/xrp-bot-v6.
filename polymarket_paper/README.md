# PAPER test: párová strategie Polymarket Up/Down

Stav: **26. 11. 2026, kód hotový a otestovaný offline (7 testů). Zatím neběží na živých datech.**

## Hypotéza (z tweetu @RetroValix, 26. 11. 2026)
Na 5m/15m krypto trzích „Up or Down“ nakupovat obě strany tak, aby průměrná
cena páru byla < 1 USDC. Jeden z kusů se vždy vyplatí 1 USDC.

## Strategie
| název | logika | riziko |
|---|---|---|
| `instant_pair` | taker nákup UP+DOWN naráz, jen když `ask_up + ask_dn + poplatky <= 0.99` | téměř žádné (pokud se plní) |
| `leg_in` | koupit stranu pod 0.45, druhou dokoupit, až je pár ≤ 0.97; max 40 nespárovaných kusů; posledních 60 s žádné nové nohy | nespárované kusy = směrová sázka |

Poplatek: `shares × rate × p × (1 − p)`, `rate` z `feeSchedule` každého trhu
(26. 11. 2026: XRP 15m = 0.01; dokumentace uvádí pro krypto až 0.07).

## Proč jsou výsledky spíš optimistické
- plnění za zobrazený ask bez latence a bez konkurence jiných botů,
- strategie jen jako taker (maker rebaty nesimulujeme),
- knihu čteme po ~3 s, skutečné příležitosti trvají milisekundy.

Kladný výsledek tedy je **nutná, ne postačující** podmínka. Záporný výsledek strategii prakticky vyřazuje.

## První pozorování (ruční snímek, 26. 11. 2026, 12:47)
XRP 15m: nejlepší ask UP 0.50, DOWN ≈ 0.54, takže součet je 1.04. Okamžitá arbitráž v tu chvíli nebyla.

## Spuštění (jen čte veřejná API, žádné klíče)
```
python -m polymarket_paper.collector       # sběr + simulace, JSONL do data/polymarket_paper
python -m polymarket_paper.report          # souhrn
python -m pytest -q test_polymarket_paper.py
```

## Kritérium úspěchu (stanoveno předem)
Alespoň 7 dní dat a 300 vyhodnocených trhů na strategii, kladný PnL po poplatcích,
a také kladný PnL v obou polovinách období zvlášť.

## Vyhodnocení po 2 dnech (28. 11. 2026, 8:55, data z Postgresu `pm_paper_events`)
| strategie | trhů | PnL USDC | výnos z nákladu | ziskových |
|---|---|---|---|---|
| instant_pair | 654 | +231,89 | +2,78 % | 100 % |
| leg_in (v1) | 2 782 | −9 094,28 | −2,94 % | 39,7 % |

Rozklad `leg_in` v1:
- plně spárované trhy (869): **+8 097 USDC**,
- trhy s nespárovanou nohou (1 917): **−17 204 USDC**,
- nespárovaná (těžší) strana prohrála v **1 904 z 1 917** trhů (99,3 %), i když se kupovala
  v průměru za 0,356.

Příčina: adverzní výběr. Když první noha vyhrává, druhá strana zlevní a pár se dokončí.
Když první noha prohrává, druhá strana podraží a pár se nedokončí, takže nespárované
zůstanou skoro vždy jen prohrávající kusy. Přikupování „levné“ strany do 40 kusů ztrátu zvětšovalo.
Parametry v1 to nespraví, problém je ve stavbě strategie.

## Změny 28. 11. 2026
- `leg_in` v1 **vypnuta** (historie zůstává v DB a na stránce).
- `leg_in_v2`: nanejvýš 1 nespárovaná dávka (10 ks), žádné přikupování,
  první noha jen za 0,25–0,45 a jen když zbývá ≥ 120 s. Nespárovanou nohu
  po 60 s nebo 45 s před koncem **prodá do bidů** (s taker poplatkem), nedrží ji do vyhodnocení.
- `instant_pair_confirmed`: arbitráž se počítá, jen když vydrží 2 snímky po sobě (~4 s).
  Ukazuje, kolik zisku `instant_pair` zbude bez okamžitých příležitostí, které by reálně
  sebral rychlejší bot.
- výběr strategií proměnnou `PM_STRATEGIES` (výchozí `instant_pair,instant_pair_confirmed,leg_in_v2`).

Kritérium úspěchu zůstává stejné (7 dní, ≥ 300 trhů, zisk v obou polovinách).
