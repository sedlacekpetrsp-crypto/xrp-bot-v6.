"""Rate-limited public market data for PAPER bots; no order/account endpoints."""
import asyncio
import copy
import json
import math
import os
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit, parse_qsl

import httpx

BUILD = "market-data-guard-20260913-4"
INTERVALS = {"1m": 1, "5m": 5, "15m": 15, "30m": 30,
             "1h": 60, "4h": 240, "1d": 1440}


class MarketDataUnavailable(RuntimeError):
    pass


def retry_seconds(response, default):
    """Never shorten a server-specified ban, including dates/epoch timestamps."""
    waits = [float(default)]
    raw = response.headers.get("Retry-After", "")
    try:
        waits.append(float(raw))
    except ValueError:
        try:
            waits.append(parsedate_to_datetime(raw).timestamp() - time.time())
        except (ValueError, TypeError, OverflowError):
            pass
    try:
        body = response.json()
        value = float(body.get("retryAfter", 0))
        if value:
            waits.append(value / 1000 - time.time() if value > 1e12 else
                         value - time.time() if value > 1e9 else value)
        match = re.search(r"banned until (\d+)", str(body.get("msg", "")))
        if match:
            waits.append(int(match.group(1)) / 1000 - time.time())
    except (ValueError, TypeError, AttributeError):
        pass
    return max(x for x in waits if math.isfinite(x))


class MarketData:
    def __init__(self):
        self.provider = "binance"
        self.blocked = {"binance": 0.0, "kraken": 0.0}
        self.cache = {}
        self.failures = {}
        self.key_locks = {}
        self.gates = {p: asyncio.Lock() for p in self.blocked}
        self.next_request = {p: 0.0 for p in self.blocked}
        self.last_success = None
        self.last_error = None
        self.last_log = 0.0
        self.requests = {p: 0 for p in self.blocked}
        self.transition_until = 0.0

    def status(self):
        return {"build": BUILD, "provider": self.provider,
                "last_success": self.last_success, "last_error": self.last_error,
                "blocked_seconds": {p: max(0, math.ceil(t - time.time())) for p, t in self.blocked.items()},
                "requests": dict(self.requests)}

    async def request(self, client, provider, url, params, timeout):
        async with self.gates[provider]:
            if provider == "binance" and self.provider != "binance":
                raise MarketDataUnavailable("Zdroj byl přepnut na Kraken")
            if self.blocked[provider] > time.time():
                raise MarketDataUnavailable(f"{provider}: čekám na konec omezení API")
            await asyncio.sleep(max(0, self.next_request[provider] - time.monotonic()))
            if self.blocked[provider] > time.time():
                raise MarketDataUnavailable(f"{provider}: čekám na konec omezení API")
            self.next_request[provider] = time.monotonic() + (1.05 if provider == "kraken" else 0.15)
            self.requests[provider] += 1
            # Hold this gate through the response so a ban stops queued requests.
            r = await client.get(url, params=params, timeout=timeout)
            if r.status_code in (418, 429):
                self.blocked[provider] = time.time() + retry_seconds(r, 3600 if r.status_code == 418 else 60)
            r.raise_for_status()
            return r.json()

    async def kraken(self, client, path, params, timeout):
        symbol = str(params.get("symbol", ""))
        if not symbol or not symbol.isalnum():
            raise MarketDataUnavailable("Chybí podporovaný obchodní pár")
        pair = "XBT" + symbol[3:] if symbol.startswith("BTC") else symbol
        query = {"pair": pair}
        if path == "/api/v3/klines":
            interval = INTERVALS.get(str(params.get("interval")))
            if interval is None:
                raise MarketDataUnavailable("Kraken nepodporuje požadovaný interval")
            query["interval"] = interval
            endpoint = "OHLC"
        elif path == "/api/v3/ticker/price":
            endpoint = "Ticker"
        elif path == "/api/v3/depth":
            endpoint = "Depth"
            query["count"] = min(500, max(1, int(params.get("limit", 20))))
        else:
            raise MarketDataUnavailable("Nepodporovaný endpoint tržních dat")
        payload = await self.request(client, "kraken", "https://api.kraken.com/0/public/" + endpoint, query, timeout)
        errors = payload.get("error") or []
        if errors:
            if any("limit" in e.lower() or "throttl" in e.lower() for e in errors):
                self.blocked["kraken"] = time.time() + 60
            raise MarketDataUnavailable(f"Kraken {symbol}: {errors}")
        result = payload.get("result") or {}
        data = next((v for k, v in result.items() if k != "last"), None)
        if not data:
            raise MarketDataUnavailable(f"Kraken: chybí data {symbol}")
        if endpoint == "OHLC":
            duration = interval * 60_000
            rows = [[int(float(x[0])*1000), str(x[1]), str(x[2]), str(x[3]), str(x[4]),
                     str(x[6]), int(float(x[0])*1000)+duration-1, "0", int(x[7]), "0", "0", "0"]
                    for x in data[-int(params.get("limit", 250)):]]
            return rows
        if endpoint == "Ticker":
            return {"symbol": symbol, "price": str(data["c"][0])}
        return {"bids": [x[:2] for x in data["bids"]], "asks": [x[:2] for x in data["asks"]]}

    def validate(self, path, params, data):
        if path == "/api/v3/klines":
            minutes = INTERVALS.get(str(params.get("interval")))
            if not data or len(data) < min(2, int(params.get("limit", 250))):
                raise MarketDataUnavailable("Prázdná historie svíček")
            if minutes and not (int(data[-1][0]) <= time.time()*1000 + 5000 and
                               int(data[-1][0]) + minutes*60_000 > time.time()*1000 - 5000):
                raise MarketDataUnavailable("Zastaralé svíčky; obchodování čeká na nová data")
            for row in data:
                if any(not math.isfinite(float(row[i])) or float(row[i]) <= 0 for i in (1, 2, 3, 4)):
                    raise MarketDataUnavailable("Neplatná cena svíčky")
        elif path == "/api/v3/ticker/price":
            price = float(data["price"])
            if not math.isfinite(price) or price <= 0:
                raise MarketDataUnavailable("Neplatná aktuální cena")
        elif path == "/api/v3/depth":
            if not data.get("bids") or not data.get("asks"):
                raise MarketDataUnavailable("Prázdná kniha objednávek")

    async def get(self, client, url, params=None, timeout=15):
        parsed = urlsplit(str(url))
        if parsed.scheme not in {"https", "http"} or not parsed.hostname:
            raise MarketDataUnavailable("Neplatná adresa zdroje dat")
        params = {**dict(parse_qsl(parsed.query)), **(params or {})}
        path = next((p for p in ("/api/v3/klines", "/api/v3/ticker/price", "/api/v3/depth")
                     if parsed.path.endswith(p)), None)
        if path is None:
            raise MarketDataUnavailable("Pouze veřejná tržní data")
        key = (parsed.netloc + parsed.path, tuple(sorted((k, str(v)) for k, v in params.items())))
        async with self.key_locks.setdefault(key, asyncio.Lock()):
            if time.monotonic() < self.transition_until:
                raise MarketDataUnavailable("Změna zdroje na Kraken; čekám na nový cyklus")
            cached = self.cache.get(key)
            now = time.monotonic()
            if cached and cached[0] > now and cached[1] == self.provider:
                self.validate(path, params, cached[2])
                return self.response(url, copy.deepcopy(cached[2]))
            failed = self.failures.get(key)
            if failed and failed[0] > now:
                raise MarketDataUnavailable(failed[1])
            try:
                if self.provider == "binance":
                    try:
                        data = await self.request(client, "binance", parsed.scheme+"://"+parsed.netloc+parsed.path, params, timeout)
                    except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.NetworkError, MarketDataUnavailable) as exc:
                        status = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
                        if status is not None and status not in (418, 429, 403, 451) and status < 500:
                            raise
                        self.provider = "kraken"
                        self.transition_until = time.monotonic() + 30
                        self.cache.clear()
                        self.last_error = f"Binance nedostupná ({status or type(exc).__name__}); PAPER zdroj Kraken"
                        print("MARKET_DATA_SOURCE", self.last_error, flush=True)
                        raise MarketDataUnavailable("Změna zdroje na Kraken; čekám na nový cyklus") from exc
                else:
                    data = await self.kraken(client, path, params, timeout)
                self.validate(path, params, data)
                ttl = 1.0 if path.endswith("price") else 0.0 if path.endswith("depth") else 15.0
                if path.endswith("klines") and params.get("interval") in INTERVALS:
                    seconds = INTERVALS[params["interval"]] * 60
                    wall_now = time.time()
                    current_bucket_ms = int(wall_now // seconds * seconds * 1000)
                    last_open_ms = int(data[-1][0])
                    if last_open_ms >= current_bucket_ms:
                        ttl = max(0.5, seconds - wall_now % seconds)
                    else:
                        ttl = 1.0
                self.cache[key] = (time.monotonic()+ttl, self.provider, copy.deepcopy(data))
                self.last_success = datetime.now(timezone.utc).isoformat()
                self.last_error = None
                self.failures.pop(key, None)
                if time.monotonic() - self.last_log > 60:
                    print("MARKET_DATA_OK", json.dumps(self.status()), flush=True)
                    self.last_log = time.monotonic()
                return self.response(url, data)
            except Exception as exc:
                self.last_error = str(exc)
                self.failures[key] = (time.monotonic()+15, str(exc))
                raise MarketDataUnavailable(str(exc)) from exc

    @staticmethod
    def response(url, data):
        return httpx.Response(200, json=data, request=httpx.Request("GET", str(url)))


market = MarketData()
market_get = market.get


def install_data_health(app):
    from fastapi.responses import JSONResponse

    if getattr(app, "title", "") == "V8 Candle Combined":
        keepalive_url = os.getenv(
            "V81_KEEPALIVE_URL",
            "https://xrp-bot-v8-1-candle.onrender.com/health",
        )
        keepalive_task = None

        async def keep_v81_awake():
            await asyncio.sleep(10)
            async with httpx.AsyncClient(follow_redirects=True) as client:
                while True:
                    try:
                        response = await client.head(keepalive_url, timeout=30)
                        print(
                            f"V81_KEEPALIVE status={response.status_code} target={keepalive_url}",
                            flush=True,
                        )
                    except Exception as exc:
                        print(f"V81_KEEPALIVE_ERROR {exc!r}", flush=True)
                    await asyncio.sleep(240)

        @app.on_event("startup")
        async def start_v81_keepalive():
            nonlocal keepalive_task
            keepalive_task = asyncio.create_task(keep_v81_awake())

        @app.on_event("shutdown")
        async def stop_v81_keepalive():
            nonlocal keepalive_task
            if keepalive_task:
                keepalive_task.cancel()
                await asyncio.gather(keepalive_task, return_exceptions=True)

    @app.get("/data-health")
    async def data_health():
        return market.status()

    @app.exception_handler(MarketDataUnavailable)
    async def unavailable(request, exc):
        return JSONResponse({"ok": False, "error": str(exc), "market_data": market.status()}, status_code=503)
