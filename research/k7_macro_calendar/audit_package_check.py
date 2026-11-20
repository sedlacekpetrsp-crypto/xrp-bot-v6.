"""K7 auditní balíček (dle ChatGPT 0292 §4) — JEN kontrola dat událostí, ŽÁDNÉ výnosy/ceny.

Čte step0_events.csv, ověří PIT a konzistenci, zmrazí seznam 69 způsobilých událostí
(events_frozen_69.csv + SHA-256). Spuštění: python -I audit_package_check.py <dir>
"""
import csv, hashlib, json, sys, re
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

def iso(s):
    return datetime.fromisoformat(s) if s else None

def eligible(r):
    return (r["pit_status"] == "PROVEN" and r["actual_at"] and r["scheduled_at"] == r["actual_at"]
            and float(r["coverage_1h"] or 0) == 1.0)

def check(d: Path):
    rows = list(csv.DictReader(open(d / "step0_events.csv", newline="")))
    out = {"rows": len(rows), "problems": []}
    ids = [r["event_id"] for r in rows]
    if len(set(ids)) != len(ids):
        out["problems"].append("duplicitní event_id")
    el = [r for r in rows if eligible(r)]
    out["eligible"] = len(el)
    leads, et_times = [], {}
    prev = None
    for r in el:
        t = iso(r["scheduled_at"]); ann = iso(r["first_announced_at"])
        if not re.fullmatch(r"[0-9a-f]{64}", r["evidence_hash"] or ""):
            out["problems"].append(f"{r['event_id']}: evidence_hash není SHA-256")
        if not ann or ann >= t - timedelta(hours=25):
            out["problems"].append(f"{r['event_id']}: oznámení není před vstupem t-25h")
        leads.append((t - ann).total_seconds() / 86400)
        loc = t.astimezone(ET).strftime("%H:%M"); et_times[loc] = et_times.get(loc, 0) + 1
        if prev and t <= prev:
            out["problems"].append(f"{r['event_id']}: není chronologicky")
        prev = t
        if "web.archive.org/web/" not in r["source_url"]:
            out["problems"].append(f"{r['event_id']}: zdroj není archivní snímek")
        snap = re.search(r"/web/(\d{14})", r["source_url"]).group(1)
        if datetime.strptime(snap, "%Y%m%d%H%M%S").replace(tzinfo=ann.tzinfo) != ann:
            out["problems"].append(f"{r['event_id']}: first_announced_at ≠ čas snímku")
    out["lead_days_min"] = round(min(leads), 1); out["lead_days_median"] = round(sorted(leads)[len(leads)//2], 1)
    out["scheduled_time_ET"] = et_times
    out["excluded"] = [r["event_id"] for r in rows if not eligible(r)]
    seg = {"ladeni": el[:35], "validace": el[35:51], "zaverecny": el[51:]}
    out["segments"] = {k: [v[0]["event_id"], v[-1]["event_id"], len(v)] for k, v in seg.items()}
    out["dates_with_cpi_note"] = [r["event_id"] for r in el if r.get("note")]
    frozen = d / "events_frozen_69.csv"
    with open(frozen, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["idx", "event_id", "t_utc", "entry_utc_t-25h", "exit_utc_t-1h", "source_url", "evidence_hash", "segment"])
        for i, r in enumerate(el, 1):
            t = iso(r["scheduled_at"]); s = "ladeni" if i <= 35 else ("validace" if i <= 51 else "zaverecny")
            w.writerow([i, r["event_id"], t.isoformat(), (t - timedelta(hours=25)).isoformat(),
                        (t - timedelta(hours=1)).isoformat(), r["source_url"], r["evidence_hash"], s])
    out["sha256_step0_events_csv"] = hashlib.sha256((d / "step0_events.csv").read_bytes()).hexdigest()
    out["sha256_events_frozen_69_csv"] = hashlib.sha256(frozen.read_bytes()).hexdigest()
    out["verdict"] = "OK" if not out["problems"] and out["eligible"] == 69 else "PROBLÉM"
    return out

if __name__ == "__main__":
    d = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent)
    res = check(d)
    (d / "audit_package_check.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(res, ensure_ascii=False, indent=1))
