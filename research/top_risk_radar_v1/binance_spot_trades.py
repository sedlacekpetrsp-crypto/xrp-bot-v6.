"""Parse Binance public SPOT trades CSV; research only, no network or trading."""
from __future__ import annotations
import csv
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from io import StringIO
from typing import Iterable
from research.top_risk_radar_v1.label_events import Trade

def epoch_to_utc(value: str) -> datetime:
    """Binance spot: milliseconds before 2025, microseconds from 2025."""
    n=int(value)
    if n <= 0:
        raise ValueError("invalid epoch")
    # 13-digit milliseconds or 16-digit microseconds; never guess from year alone.
    if 10**12 <= n < 10**14:
        microseconds=n*1000
    elif 10**15 <= n < 10**17:
        microseconds=n
    else:
        raise ValueError("unexpected timestamp magnitude")
    return datetime(1970,1,1,tzinfo=timezone.utc) + timedelta(microseconds=microseconds)

def parse_spot_trades_csv(lines: Iterable[str]) -> list[Trade]:
    """Binance archive order: id,price,qty,quoteQty,time,isBuyerMaker,isBestMatch.
    Accept optional documented header; reject malformed and non-monotonic input.
    Multiple trades at the same timestamp are legitimate and not deduplicated.
    """
    reader=csv.reader(lines)
    result=[]
    prev=None
    prev_id=None
    for row_number,row in enumerate(reader,1):
        if not row:
            continue
        if row_number==1 and row[0].strip().lower() in ("id","trade id"):
            continue
        if len(row)!=7:
            raise ValueError(f"row {row_number}: expected 7 columns")
        if not row[0].strip().isdigit():
            raise ValueError(f"row {row_number}: invalid trade id")
        try:
            trade=Trade(epoch_to_utc(row[4]),Decimal(row[1]),int(row[0]))
            if any(not Decimal(v).is_finite() or Decimal(v) <= 0 for v in row[2:4]):
                raise ValueError("nonpositive/nonfinite quantity")
            if any(v not in ("true", "false", "True", "False") for v in row[5:7]):
                raise ValueError("invalid boolean flag")
        except (ValueError,ArithmeticError) as exc:
            raise ValueError(f"row {row_number}: invalid trade") from exc
        if prev is not None and trade.timestamp < prev:
            raise ValueError(f"row {row_number}: non-monotonic timestamp")
        if prev_id is not None and trade.trade_id <= prev_id:
            raise ValueError(f"row {row_number}: duplicate or non-monotonic trade ID")
        result.append(trade)
        prev=trade.timestamp
        prev_id=trade.trade_id
    return result
