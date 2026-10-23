"""Public OKX XRP swap confirmation; no credentials or order endpoints.

This is a different venue/population from Binance (OKX top 5% traders).
Use one venue for all three observations, never fill missing values.
Documentation: https://www.okx.com/docs-v5/en/#trading-statistics-rest-api
"""
import asyncio
import math

BASE = 'https://www.okx.com/api/v5/rubik/stat/'
STEP = 300000
PATHS = ('contracts/open-interest-history',
         'contracts/long-short-position-ratio-contract-top-trader',
         'taker-volume-contract')


def closed_rows(rows, stamp, width):
    if not isinstance(rows, list):
        raise ValueError('Invalid OKX data array')
    selected = {}
    for row in rows:
        if not isinstance(row, list) or len(row) < width:
            raise ValueError('Invalid OKX data row')
        ts = int(row[0])
        # Conservatively exclude the entire current bucket for every series.
        if ts % STEP or ts <= 0:
            raise ValueError('Invalid OKX timestamp')
        values = [float(v) for v in row[1:width]]
        if not all(math.isfinite(v) and v > 0 for v in values):
            raise ValueError('Invalid or empty OKX observation')
        if ts + STEP <= stamp:
            if ts in selected:
                raise ValueError('Duplicate OKX observation')
            selected[ts] = values
    if not selected or max(selected) != stamp - STEP:
        raise ValueError('Stale OKX confirmation data')
    return selected


def normalize(oi, top, taker, stamp):
    o = closed_rows(oi, stamp, 2)
    t = closed_rows(top, stamp, 2)
    v = closed_rows(taker, stamp, 3)
    latest = stamp - STEP
    if latest - STEP not in o:
        raise ValueError('Missing consecutive OKX open interest')
    return (
        [dict(timestamp=ts, sumOpenInterest=o[ts][0]) for ts in (latest-STEP,latest)],
        [dict(timestamp=latest, longShortRatio=t[latest][0])],
        [dict(timestamp=latest, buySellRatio=v[latest][1]/v[latest][0])],
    )


async def fetch(client, stamp):
    async def get(path):
        r = await client.get(BASE + path, params=dict(instId='XRP-USDT-SWAP',period='5m',limit=8))
        r.raise_for_status()
        data = r.json()
        if not isinstance(data,dict) or data.get('code') != '0':
            raise ValueError('OKX statistics request rejected')
        return data.get('data')
    rows = await asyncio.gather(*(get(path) for path in PATHS))
    return normalize(*rows, stamp)
