"""K9 fáze A runner (mikrostruktura, ŽÁDNÝ výnos, žádný obchod).

Načte jen měsíce se stavem OK v `step0_manifest.json`, znovu stáhne ZIP z Binance Vision a ověří, že SHA-256 je
SHODNÉ s manifestem kroku 0 (jinak konec s chybou — data by nebyla identická s auditem). Pak zavolá
`phase_a.run` (PROTOCOL.md zmrazený 2026-11-16 + dodatek 1) a zapíše:
- `phaseA_results.json` (D1/D2 obou období, CI, valid_reps, per-asset, brána, síla),
- `phaseA_power_table.csv`, `phaseA_exposure.csv`,
- `phaseA_events.csv.gz` (všechny události pro nezávislý přepočet D z jednotlivých řádků).
Spouští se v GitHub Actions (sandbox nemá přístup na data.binance.vision).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from research.k9_round_number import audit, phase_a


def load_frames(manifest: dict, datadir: Path, fetch=audit.download_month) -> dict[str, pd.DataFrame]:
    frames: dict[str, list[pd.DataFrame]] = {}
    for rec in manifest["months"]:
        if rec["status"] != "OK":
            continue  # vyloučené měsíce kroku 0 se nepoužijí ani neimputují
        y, m = map(int, rec["month"].split("-"))
        zp, _ = fetch(rec["symbol"], y, m, datadir / rec["symbol"])
        if zp is None:
            raise RuntimeError(f"{rec['symbol']} {rec['month']}: soubor zmizel od kroku 0")
        got = audit.sha256_file(Path(zp))
        if got != rec["sha256"]:
            raise RuntimeError(f"{rec['symbol']} {rec['month']}: SHA-256 {got} ≠ manifest {rec['sha256']}")
        df = audit.read_kline_zip(Path(zp))
        lo = pd.Timestamp(year=y, month=m, day=1, tz="UTC")
        df = df[(df.index >= lo) & (df.index < lo + pd.offsets.MonthBegin(1))]
        frames.setdefault(rec["symbol"], []).append(df)
        Path(zp).unlink(missing_ok=True)
    return {s: pd.concat(v).sort_index() for s, v in frames.items()}


def _jsonable(res: dict) -> dict:
    return {k: v for k, v in res.items() if k not in ("power_table", "exposure", "events")}


def run(manifest_path: Path, outdir: Path, datadir: Path, reps: int = phase_a.REPS, fetch=audit.download_month) -> dict:
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("gate", {}).get("verdict") != "DATA GO":
        raise RuntimeError("krok 0 není DATA GO — fáze A se nespouští")
    frames = load_frames(manifest, datadir, fetch)
    res = phase_a.run(frames, reps=reps)
    outdir.mkdir(parents=True, exist_ok=True)
    res["power_table"].to_csv(outdir / "phaseA_power_table.csv", index=False)
    res["exposure"].to_csv(outdir / "phaseA_exposure.csv", index=False)
    res["events"].to_csv(outdir / "phaseA_events.csv.gz", index=False)
    payload = {"protocol": "research/k9_round_number/PROTOCOL.md (+ dodatek 1)", "phase": "A",
               "step0_manifest_sha256": audit.sha256_file(manifest_path), "reps": reps, **_jsonable(res)}
    (outdir / "phaseA_results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1, default=str))
    return res


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, default=Path("research/k9_round_number/step0_manifest.json"))
    p.add_argument("--outdir", type=Path, default=Path("research/k9_round_number"))
    p.add_argument("--datadir", type=Path, default=Path("/tmp/k9_vision"))
    a = p.parse_args(argv)
    res = run(a.manifest, a.outdir, a.datadir)
    print(json.dumps(_jsonable(res), ensure_ascii=False, indent=1, default=str))
    print(f"VERDIKT FÁZE A: {res['gate']['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
