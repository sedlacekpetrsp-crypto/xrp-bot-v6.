"""K9 fáze B runner (PAPER výzkum, dodatek 2 + oprava 1). FAIL CLOSED.

Dvě oddělené fáze, každá samostatným spuštěním v GitHub Actions:
  --stage dev    výnosy JEN z vývojového období (t < 2024-01-01) ⇒ `phaseB_dev_selection.json` (předbrána, H*)
                 + `phaseB_dev_trades.csv.gz`. Závěrečný úsek se nenačítá do obchodů.
  --stage final  jen když je `phaseB_dev_selection.json` commitnutý v HEAD (bajtově shodný), `final_open` = true
                 a SHA-256 PROTOCOL.md se shoduje s výběrem ⇒ jen H*, brány a)–g), trades.csv, results.json.

Obě fáze vyžadují v `--owner-decisions` řádek začínající datem a obsahující „SCHVÁLENO: výkonnost K9“
(soubor z větve dialog/claude-chatgpt; workflow ho stáhne). Bez něj se nic nenačte ani nespočte.
Data = stejné měsíce a SHA-256 jako manifest kroku 0 (jinak chyba), sloupec `open` navíc ke čtení fáze A.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from research.k9_round_number import audit, phase_b
from research.k9_round_number.events import STEPS

HERE = Path("research/k9_round_number")
APPROVAL_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\s+SCHVÁLENO:\s*výkonnost K9\b", re.M)
SELECTION = "phaseB_dev_selection.json"


class NotApproved(RuntimeError):
    pass


def check_approval(text: str) -> None:
    if not APPROVAL_RE.search(text or ""):
        raise NotApproved("v OWNER_DECISIONS chybí řádek „<datum> SCHVÁLENO: výkonnost K9“ — výkon se nespouští")


def read_with_open(path: Path) -> pd.DataFrame:
    """Jako audit.read_kline_zip, ale navíc sloupec open (čtení fáze A se nemění)."""
    import io
    import zipfile
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if n.endswith(".csv")]
        if len(names) != 1:
            raise ValueError(f"ZIP musí obsahovat právě 1 CSV, má {len(names)}")
        raw = z.read(names[0]).decode()
    header = 0 if raw.split("\n", 1)[0].startswith("open_time") else None
    df = pd.read_csv(io.StringIO(raw), header=header, names=None if header == 0 else audit.KLINE_COLS)
    df.columns = audit.KLINE_COLS[: len(df.columns)]
    out = df[["open", "high", "low", "close", "volume", "taker_buy"]].astype(float)
    out.index = audit._to_utc(df["open_time"])
    return out[~out.index.duplicated(keep="first")].sort_index()


def load_frames(manifest: dict, datadir: Path, fetch=audit.download_month, reader=read_with_open) -> dict[str, pd.DataFrame]:
    frames: dict[str, list[pd.DataFrame]] = {}
    for rec in manifest["months"]:
        if rec["status"] != "OK":
            continue
        y, m = map(int, rec["month"].split("-"))
        zp, _ = fetch(rec["symbol"], y, m, datadir / rec["symbol"])
        if zp is None:
            raise RuntimeError(f"{rec['symbol']} {rec['month']}: soubor zmizel od kroku 0")
        got = audit.sha256_file(Path(zp))
        if got != rec["sha256"]:
            raise RuntimeError(f"{rec['symbol']} {rec['month']}: SHA-256 {got} ≠ manifest {rec['sha256']}")
        df = reader(Path(zp))
        lo = pd.Timestamp(year=y, month=m, day=1, tz="UTC")
        frames.setdefault(rec["symbol"], []).append(df[(df.index >= lo) & (df.index < lo + pd.offsets.MonthBegin(1))])
        Path(zp).unlink(missing_ok=True)
    return {s: pd.concat(v).sort_index() for s, v in frames.items()}


def committed_bytes(path: Path) -> bytes | None:
    try:
        return subprocess.run(["git", "show", f"HEAD:{path.as_posix()}"], capture_output=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def stage_dev(frames: dict[str, pd.DataFrame], protocol_sha: str) -> tuple[dict, pd.DataFrame]:
    dev_tr, missing = {}, {}
    for H in phase_b.HORIZONS:
        parts, stats = [], {}
        for a, df in frames.items():
            df = df[df.index < audit.DEV_END]  # závěrečný úsek se v této fázi vůbec nepoužije
            tr, _, st = phase_b.asset_trades(df, STEPS[a], H, a)
            parts.append(phase_b.split(tr, "dev"))
            stats[a] = st
        dev_tr[H] = pd.concat(parts, ignore_index=True)
        missing[H] = phase_b.missing_frac(stats, "dev")
    sel = phase_b.dev_selection(dev_tr, missing)
    sel.update({"protocol_sha256": protocol_sha, "dsr_n": phase_b.DSR_N, "stage": "dev"})
    return sel, pd.concat(dev_tr.values(), ignore_index=True)


def stage_final(frames: dict[str, pd.DataFrame], sel: dict, power_table: dict, reps: int = phase_b.REPS) -> tuple[dict, pd.DataFrame]:
    if not sel.get("final_open") or sel.get("h_star") not in phase_b.HORIZONS:
        raise RuntimeError(f"závěr se neotevírá: {sel.get('verdict')}")
    H = int(sel["h_star"])
    rng = np.random.default_rng(phase_b.SEED)
    trs, rands, grids, stats = [], [], {}, {}
    for a in sorted(frames):
        tr, g, st = phase_b.asset_trades(frames[a], STEPS[a], H, a)
        fin = phase_b.split(tr, "final")
        trs.append(fin)
        grids[a], stats[a] = g, st
        rands.append(phase_b.random_trades(g, fin[fin["kind"] == "round"].sort_values("time"), H, rng))
    tr = pd.concat(trs, ignore_index=True)
    rnd, plc = tr[tr["kind"] == "round"], tr[tr["kind"] == "placebo"]
    rand = pd.concat(rands, ignore_index=True)
    end = max(g.index.max() for g in grids.values())
    pnl = phase_b.daily_pnl(rnd, audit.DEV_END, end)
    power = power_table.get(f"H{H}_final_round", {}).get(phase_b.POWER_KEY[H])
    res = phase_b.evaluate_final(rnd, plc, rand, pnl, power, phase_b.missing_frac(stats, "final"), reps)
    res.update({"h_star": H, "n_round": int(len(rnd)), "n_placebo": int(len(plc)), "n_random": int(len(rand)),
                "max_drawdown_daily_x1": phase_b.max_drawdown(pnl),
                "exposure": phase_b.exposure(grids, rnd, audit.DEV_END),
                "benchmarks": phase_b.benchmarks(grids, rnd, audit.DEV_END)})
    return res, tr


def main(argv=None) -> int:  # pragma: no cover — síťové; logika je v testovaných funkcích
    p = argparse.ArgumentParser()
    p.add_argument("--stage", choices=("dev", "final"), required=True)
    p.add_argument("--owner-decisions", type=Path, required=True)
    p.add_argument("--manifest", type=Path, default=HERE / "step0_manifest.json")
    p.add_argument("--outdir", type=Path, default=HERE)
    p.add_argument("--datadir", type=Path, default=Path("/tmp/k9_vision"))
    a = p.parse_args(argv)
    check_approval(a.owner_decisions.read_text() if a.owner_decisions.exists() else "")
    manifest = json.loads(a.manifest.read_text())
    if manifest.get("gate", {}).get("verdict") != "DATA GO":
        raise RuntimeError("krok 0 není DATA GO")
    protocol_sha = audit.sha256_file(HERE / "PROTOCOL.md")
    sel_path = a.outdir / SELECTION
    if a.stage == "final":
        sel_bytes = sel_path.read_bytes() if sel_path.exists() else None
        if sel_bytes is None or committed_bytes(sel_path) != sel_bytes:
            raise RuntimeError("výběr H* není commitnutý v HEAD (bajtově) — závěr se neotevírá")
        sel = json.loads(sel_bytes)
        if sel.get("protocol_sha256") != protocol_sha:
            raise RuntimeError("PROTOCOL.md se změnil od výběru H* — závěr se neotevírá")
        if not sel.get("final_open"):
            raise RuntimeError(f"závěr se neotevírá: {sel.get('verdict')}")
    frames = load_frames(manifest, a.datadir)
    common = {"protocol": "research/k9_round_number/PROTOCOL.md (dodatek 2 + oprava 1)", "protocol_sha256": protocol_sha,
              "step0_manifest_sha256": audit.sha256_file(a.manifest)}
    if a.stage == "dev":
        sel, dev_tr = stage_dev(frames, protocol_sha)
        dev_tr.to_csv(a.outdir / "phaseB_dev_trades.csv.gz", index=False)
        sel_path.write_text(json.dumps({**common, **sel}, ensure_ascii=False, indent=1, default=str))
        print(json.dumps(sel, ensure_ascii=False, indent=1, default=str))
        print(f"VERDIKT VÝVOJE: {sel['verdict']}")
        return 0
    power_table = json.loads((HERE / "phaseB_power_table.json").read_text())
    res, tr = stage_final(frames, sel, power_table)
    tr.to_csv(a.outdir / "phaseB_trades.csv", index=False)
    phase_b.breakdown(tr[tr["kind"] == "round"]).to_csv(a.outdir / "phaseB_breakdown.csv", index=False)
    (a.outdir / "phaseB_results.json").write_text(json.dumps({**common, **res}, ensure_ascii=False, indent=1, default=str))
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
    print(f"VERDIKT FÁZE B: {res['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
