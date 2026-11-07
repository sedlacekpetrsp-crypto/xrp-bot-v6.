"""Download one fixed Binance XRPUSDT daily trade archive for data QA only.

No trading endpoints, credentials, strategy fitting or performance metrics.
"""
from __future__ import annotations
import csv
import hashlib
import io
import json
import re
import urllib.request
import zipfile
from datetime import datetime, timezone
from decimal import Decimal
from research.top_risk_radar_v1.binance_spot_trades import epoch_to_utc

DAY="2024-01-02"
BASE="https://data.binance.vision/data/spot/daily/trades/XRPUSDT/"
NAME=f"XRPUSDT-trades-{DAY}.zip"
MAX_BYTES=150_000_000

def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url,timeout=90) as response:
        payload=response.read(MAX_BYTES+1)
    if len(payload)>MAX_BYTES:
        raise ValueError("archive exceeds safety size limit")
    return payload

def analyze(zip_bytes: bytes, checksum_text: str) -> dict:
    m=re.search(r"\b([0-9a-fA-F]{64})\b",checksum_text)
    if not m:
        raise ValueError("missing sha256 in checksum")
    actual=hashlib.sha256(zip_bytes).hexdigest()
    if actual.lower()!=m.group(1).lower():
        raise ValueError("checksum mismatch")
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        members=[x for x in z.infolist() if not x.is_dir()]
        if len(members)!=1 or not members[0].filename.endswith(".csv"):
            raise ValueError("unexpected archive members")
        if members[0].file_size>2_000_000_000:
            raise ValueError("uncompressed file too large")
        first=last=None
        count=0
        duplicates=0
        prev=None
        with z.open(members[0]) as raw:
            for row in csv.reader(io.TextIOWrapper(raw,encoding="utf-8-sig")):
                if not row: continue
                if count==0 and row[0].strip().lower()=="id": continue
                if len(row)!=7: raise ValueError("unexpected CSV columns")
                if not row[0].isdigit() or Decimal(row[1])<=0:
                    raise ValueError("invalid trade row")
                ts=epoch_to_utc(row[4])
                if prev is not None and ts<prev:
                    raise ValueError("nonmonotonic timestamps")
                duplicates+=int(prev==ts)
                if first is None: first=ts
                last=prev=ts
                count+=1
    if count==0: raise ValueError("empty archive")
    expected=datetime.fromisoformat(DAY).replace(tzinfo=timezone.utc).date()
    if first.date()!=expected or last.date()!=expected:
        raise ValueError("trade dates do not match archive")
    return {"provider":"Binance public data","venue":"Binance","market_type":"spot",
            "symbol":"XRPUSDT","date_utc":DAY,"archive":NAME,
            "raw_sha256":actual,"checksum_verified":True,
            "row_count":count,"first_trade_utc":first.isoformat(),
            "last_trade_utc":last.isoformat(),
            "same_timestamp_adjacent_pairs":duplicates,
            "coverage_status":"not_yet_independently_verified",
            "point_in_time_feature_qa":"not_performed"}

if __name__=="__main__":
    blob=fetch(BASE+NAME)
    checksum=fetch(BASE+NAME+".CHECKSUM").decode("utf-8")
    print(json.dumps(analyze(blob,checksum),indent=2,sort_keys=True))
