"""Validate source metadata before XRP radar research. No downloads or trades."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Mapping
import re

FIELDS=("source_id","provider","market_type","venue","symbol","timezone","start_utc","end_utc","event_timestamp_field","granularity","acquisition_utc","raw_sha256","row_count","point_in_time_supported","qa_status")

def validate_manifest(record: Mapping[str,object]) -> list[str]:
    issues=[]
    for field in FIELDS:
        if field not in record or record[field] is None or record[field] == "":
            issues.append("missing:"+field)
    if issues:
        return issues
    if record["timezone"] != "UTC":
        issues.append("timezone_not_utc")
    if not isinstance(record["raw_sha256"],str) or re.fullmatch(r"[0-9a-f]{64}",record["raw_sha256"]) is None:
        issues.append("invalid_sha256")
    if type(record["row_count"]) is not int or record["row_count"] <= 0:
        issues.append("invalid_row_count")
    for k in ("start_utc","end_utc","acquisition_utc"):
        try:
            dt=datetime.fromisoformat(str(record[k]).replace("Z","+00:00"))
            if dt.tzinfo is None or dt.utcoffset() != timezone.utc.utcoffset(dt):
                issues.append("non_utc:"+k)
        except (ValueError,TypeError):
            issues.append("invalid_timestamp:"+k)
    try:
        start=datetime.fromisoformat(str(record["start_utc"]).replace("Z","+00:00"))
        end=datetime.fromisoformat(str(record["end_utc"]).replace("Z","+00:00"))
        if start>=end:
            issues.append("invalid_coverage_range")
        acquired=datetime.fromisoformat(str(record["acquisition_utc"]).replace("Z","+00:00"))
        if acquired.tzinfo is not None and end.tzinfo is not None and acquired < end:
            issues.append("acquisition_before_coverage_end")
    except (ValueError,TypeError):
        pass
    if type(record["point_in_time_supported"]) is not bool:
        issues.append("invalid_pit_flag")
    if record["qa_status"] not in ("pending","verified","rejected"):
        issues.append("invalid_qa_status")
    return issues
