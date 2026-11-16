"""K9 krok 0 runner: stáhne Binance Vision UM klines 1m (ZIP + CHECKSUM), ověří SHA-256 a pokrytí, zapíše manifest.

Jen datový audit podle PROTOCOL.md (zmrazeno 2026-11-16 + dodatek 1). Nepočítá metriky fáze A ani výnosy.
Spouští se v GitHub Actions (sandbox nemá přístup na data.binance.vision). ZIPy se necommitují; commituje se
jen manifest se SHA-256 každého souboru a souhrn, aby fáze A mohla ověřit identitu dat.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from research.k9_round_number import audit


def run(outdir: Path, datadir: Path) -> dict:
    records = []
    for sym in audit.ASSETS:
        for y, m in audit.months():
            zp, cp = audit.download_month(sym, y, m, datadir / sym)
            rec = audit.audit_month(sym, y, m, zp, cp)
            records.append(rec)
            print(f"{sym} {rec.month} {rec.status} cov={rec.coverage:.4f} sha={rec.sha256[:12]}", flush=True)
            if zp is not None:  # šetří disk runneru; identita je v manifestu
                Path(zp).unlink(missing_ok=True)
    outdir.mkdir(parents=True, exist_ok=True)
    g = audit.write_manifest(records, outdir / "step0_manifest.json")
    return g


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--outdir", type=Path, default=Path("research/k9_round_number"))
    p.add_argument("--datadir", type=Path, default=Path("/tmp/k9_vision"))
    a = p.parse_args(argv)
    g = run(a.outdir, a.datadir)
    print(json.dumps(g, ensure_ascii=False, indent=1))
    print(f"VERDIKT KROKU 0: {g['verdict']} ({g['ok_months']}/{g['total_months']} měsíců OK)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
