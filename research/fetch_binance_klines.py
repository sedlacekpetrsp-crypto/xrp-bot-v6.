"""Download public monthly Binance spot candles; never uses API keys or trading endpoints.

Uses Binance Vision public monthly ZIP archives and verifies full month coverage.
Usage: python -m research.fetch_binance_klines BTCUSDT 5m history.csv
"""
import csv
import io
import sys
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone, timedelta
from calendar import monthrange

SYMBOLS = {"BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"}
INTERVALS = {"5m": 300000, "15m": 900000}
# Twelve full months: 2025-10 through 2026-09.
MONTHS = [(2025 + (9 + n)//12, (9 + n)%12 + 1) for n in range(12)]

def download(symbol, interval, destination):
    if symbol not in SYMBOLS or interval not in INTERVALS:
        raise ValueError("Unsupported symbol or interval")
    step = INTERVALS[interval]
    with open(destination, "w", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(["timestamp","open","high","low","close","volume"])
        previous = None
        total = 0
        for year, month in MONTHS:
            filename = f"{symbol}-{interval}-{year}-{month:02d}.zip"
            url = f"https://data.binance.vision/data/spot/monthly/klines/{symbol}/{interval}/{filename}"
            req = urllib.request.Request(url, headers={"User-Agent":"research-sweep-backtest/1.0"})
            try:
                with urllib.request.urlopen(req, timeout=90) as response:
                    payload = response.read()
            except (urllib.error.URLError, TimeoutError) as exc:
                raise RuntimeError(f"Missing archive {filename}: {exc}") from exc
            start = int(datetime(year,month,1,tzinfo=timezone.utc).timestamp()*1000)
            end = int((datetime(year+1,1,1,tzinfo=timezone.utc) if month==12 else datetime(year,month+1,1,tzinfo=timezone.utc)).timestamp()*1000)
            expected = (end-start)//step
            count = 0
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                files = [name for name in archive.namelist() if name.endswith(".csv")]
                if len(files) != 1:
                    raise ValueError(f"Unexpected ZIP contents: {filename}")
                with archive.open(files[0]) as raw:
                    for record in csv.reader(io.TextIOWrapper(raw, encoding="utf-8")):
                        if not record or not record[0].isdigit():
                            continue
                        ts = int(record[0])
                        # Binance archives can use microsecond timestamps from 2025.
                        if ts > 10**14:
                            ts //= 1000
                        if not start <= ts < end:
                            raise ValueError(f"Out-of-month timestamp: {filename}")
                        if previous is not None and ts-previous != step:
                            raise ValueError(f"Gap or duplicate in {filename}: {ts-previous} ms")
                        previous = ts
                        writer.writerow([datetime.fromtimestamp(ts/1000,timezone.utc).isoformat(),*record[1:6]])
                        count += 1
            if count != expected:
                raise ValueError(f"Incomplete {filename}: {count} candles, expected {expected}")
            total += count
            print(f"Verified {filename}: {count} bars", flush=True)
    return total

if __name__ == "__main__":
    print(f"Total bars: {download(sys.argv[1],sys.argv[2],sys.argv[3])}")
