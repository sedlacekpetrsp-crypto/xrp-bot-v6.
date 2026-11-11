"""Replay the already-audited fixed archive through the repaired parser.

Explicit manual QA entrypoint only. No labels, fit, backtest or predictions.
Raw input is held in memory and never committed. Reuses checksum/size guards.
"""
import hashlib
import io
import json
import zipfile
from datetime import datetime, timedelta, timezone

from research.top_risk_radar_v1.binance_spot_trades import parse_spot_trades_csv
from research.top_risk_radar_v1.coverage_qa import audit_coverage
from research.top_risk_radar_v1.inspect_one_archive import BASE, NAME, analyze, fetch


def replay(blob: bytes, checksum: str) -> dict:
    original = analyze(blob, checksum)
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        member = next(x for x in archive.infolist() if not x.is_dir())
        with archive.open(member) as stream:
            rows = parse_spot_trades_csv(io.TextIOWrapper(stream, encoding="utf-8-sig"))
    # Descriptive feed QA on one minute; not a 14/30-day label coverage claim.
    start = datetime(2024, 1, 2, 0, 5, tzinfo=timezone.utc)
    report = audit_coverage(start, rows, start + timedelta(minutes=1),
                            horizon=timedelta(minutes=1), max_gap=timedelta(seconds=5))
    source_paths = ["research/top_risk_radar_v1/" + name for name in
                    ("replay_trade_archive.py", "binance_spot_trades.py", "label_events.py", "coverage_qa.py", "inspect_one_archive.py")]
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    return {
        "status": "REAL_ARCHIVE_PARSER_QA_ONLY_NOT_PREDICTIVE_VALIDATION",
        "replayed_at": datetime.now(timezone.utc).isoformat(),
        "source_url": BASE + NAME,
        "checksum_url": BASE + NAME + ".CHECKSUM",
        "source": original,
        "code_sha256": {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in source_paths},
        "parsed_rows": len(rows),
        "first_trade_id": rows[0].trade_id,
        "last_trade_id": rows[-1].trade_id,
        "missing_trade_ids": sum(b.trade_id - a.trade_id - 1 for a, b in zip(rows, rows[1:])),
        "one_minute_qa": {
            "decision_at": start.isoformat(), "horizon_seconds": 60,
            "max_gap_limit_seconds": 5,
            "trades": report.trades,
            "same_timestamp_pairs": report.duplicate_timestamps,
            "max_gap_seconds": report.max_gap_seconds,
            "identity_status": report.identity_status,
            "missing_trade_ids": report.missing_trade_ids,
            "heuristic_acceptable": report.acceptable,
            "reason": report.reason,
        },
        "limits": ["Single known archive; no new historical census.",
                   "Identity continuity does not prove cross-feed accuracy or PIT feature availability.",
                   "One-minute QA cannot establish 14/30-day coverage or predictive reliability."],
    }


if __name__ == "__main__":
    print(json.dumps(replay(fetch(BASE + NAME), fetch(BASE + NAME + ".CHECKSUM").decode("utf-8")),
                     indent=2, sort_keys=True))
