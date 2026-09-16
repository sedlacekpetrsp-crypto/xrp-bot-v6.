import asyncio
import copy
import os

try:
    import httpx
    import market_data
    from fastapi.responses import JSONResponse, Response

    _original_install_data_health = market_data.install_data_health

    async def _direct_binance_price(client, symbol):
        last_exc = None
        for base in ("https://data-api.binance.vision", "https://api.binance.com"):
            try:
                r = await client.get(
                    base + "/api/v3/ticker/price",
                    params={"symbol": symbol},
                    timeout=5,
                    headers={"Cache-Control": "no-cache"},
                )
                r.raise_for_status()
                px = float(r.json()["price"])
                if px > 0:
                    return px
            except Exception as exc:
                last_exc = exc
        raise RuntimeError(f"Binance live ticker unavailable for {symbol}: {last_exc}")

    def _patched_install_data_health(app):
        _original_install_data_health(app)

        if getattr(app, "title", "") != "V8 Candle Combined":
            return

        keepalive_task = None
        keepalive_target = os.getenv(
            "V81_KEEPALIVE_URL",
            "https://xrp-bot-v8-1-candle.onrender.com/health",
        )

        async def _keep_v81_awake():
            await asyncio.sleep(20)
            async with httpx.AsyncClient(follow_redirects=True) as client:
                while True:
                    try:
                        r = await client.head(keepalive_target, timeout=30)
                        print(
                            f"V81_KEEPALIVE status={r.status_code} target={keepalive_target}",
                            flush=True,
                        )
                    except Exception as exc:
                        print(f"V81_KEEPALIVE_ERROR {exc!r}", flush=True)
                    await asyncio.sleep(240)

        @app.on_event("startup")
        async def _start_v81_keepalive():
            nonlocal keepalive_task
            keepalive_task = asyncio.create_task(_keep_v81_awake())

        @app.on_event("shutdown")
        async def _stop_v81_keepalive():
            nonlocal keepalive_task
            if keepalive_task:
                keepalive_task.cancel()
                await asyncio.gather(keepalive_task, return_exceptions=True)

        @app.middleware("http")
        async def _combined_live_price_middleware(request, call_next):
            if request.url.path == "/analyze":
                try:
                    import app_v8_candle_scanner as combined

                    fixed_data = copy.deepcopy(combined.snapshot("fixed"))
                    scanner_data = copy.deepcopy(combined.snapshot("scanner"))
                    live_errors = {}

                    async with httpx.AsyncClient() as client:
                        fp = fixed_data.get("position")
                        if fp:
                            fsymbol = fp.get("symbol") or fixed_data.get("symbol") or "XRPUSDT"
                            try:
                                px = await _direct_binance_price(client, fsymbol)
                                fixed_data["price"] = px
                                upnl = combined.fixed.unrealized(px)
                                fixed_data["unrealized_pnl"] = upnl
                                fixed_data["equity"] = float(fixed_data.get("balance", 0.0)) + upnl
                                fixed_data["time"] = combined.utcnow().isoformat()
                                fixed_data["live_price_ok"] = True
                                fixed_data["price_source"] = "BINANCE_SPOT"
                            except Exception as exc:
                                fixed_data["live_price_ok"] = False
                                live_errors["fixed"] = str(exc)

                        sp = scanner_data.get("position")
                        if sp:
                            symbol = sp.get("symbol") or scanner_data.get("symbol") or "XRPUSDT"
                            try:
                                px = await _direct_binance_price(client, symbol)
                                scanner_data["price"] = px
                                upnl = combined.scanner.est_net_unit(
                                    sp["side"], float(sp["entry_price"]), px
                                ) * float(sp["qty"])
                                scanner_data["unrealized_pnl"] = upnl
                                scanner_data["equity"] = float(scanner_data.get("balance", 0.0)) + upnl
                                scanner_data["time"] = combined.utcnow().isoformat()
                                scanner_data["live_price_ok"] = True
                                scanner_data["price_source"] = "BINANCE_SPOT"
                            except Exception as exc:
                                scanner_data["live_price_ok"] = False
                                live_errors["scanner"] = str(exc)

                    return JSONResponse({
                        "fixed": fixed_data,
                        "scanner": scanner_data,
                        "monitoring": combined.runtime_status(),
                        "time": combined.utcnow().isoformat(),
                        "live_price_source": "BINANCE_SPOT",
                        "live_price_refresh_seconds": 3,
                        "live_price_errors": live_errors,
                    }, headers={"Cache-Control": "no-store, no-cache, must-revalidate"})
                except Exception as exc:
                    print("COMBINED LIVE PRICE FALLBACK:", repr(exc), flush=True)

            response = await call_next(request)

            if request.url.path == "/" and response.headers.get("content-type", "").startswith("text/html"):
                body = getattr(response, "body", None)
                if body is None:
                    body = b"".join([chunk async for chunk in response.body_iterator])
                text = body.decode("utf-8")
                text = text.replace("setInterval(go,15000)", "setInterval(go,3000)")
                return Response(
                    content=text,
                    status_code=response.status_code,
                    headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
                    media_type="text/html",
                )

            return response

    market_data.install_data_health = _patched_install_data_health

    # Add the same confirmed Fibonacci 0.618-0.786 pullback setup to the
    # combined V8 Fixed and V8 Scanner engines without changing their current
    # breakout/momentum priority.
    from fib_strategy import fib_pullback
    import app_v8_candle as _fixed
    import v8_candle_scanner_engine as _scanner

    _fixed_detect_signal = _fixed.detect_signal

    def _fixed_detect_signal_with_fib(main_closed, structure_closed):
        base = _fixed_detect_signal(main_closed, structure_closed)
        if base.get("side") in ("LONG", "SHORT"):
            return base
        if len(main_closed) < 33:
            return base
        highs = [float(x["high"]) for x in main_closed]
        lows = [float(x["low"]) for x in main_closed]
        closes = [float(x["close"]) for x in main_closed]
        volumes = [float(x["volume"]) for x in main_closed]
        fib = fib_pullback(
            highs, lows, closes, volumes,
            lookback=30, min_impulse_pct=0.0045, min_volume_ratio=0.85,
        )
        if not fib:
            return base
        cur = main_closed[-1]
        structure_closes = [float(x["close"]) for x in structure_closed]
        e20 = _fixed.ema(structure_closes, 20)
        e50 = _fixed.ema(structure_closes, 50)
        if not e20 or not e50:
            return base
        trend = "LONG" if e20 > e50 else "SHORT" if e20 < e50 else "MIXED"
        strength = abs(e20 - e50) / max(float(cur["close"]), 1e-12)
        side = fib["signal"]
        if side != trend or strength < _fixed.MIN_TREND_STRENGTH:
            return base
        p_low = min(float(x["low"]) for x in main_closed[-4:])
        p_high = max(float(x["high"]) for x in main_closed[-4:])
        entry = float(cur["close"])
        trigger = entry * (0.9999 if side == "LONG" else 1.0001)
        return {
            "side": side,
            "setup": "FIB_0618_0786",
            "score": _fixed.MIN_SCORE,
            "support": base.get("support"),
            "resistance": base.get("resistance"),
            "pattern_low": p_low,
            "pattern_high": p_high,
            "entry": entry,
            "candle_time": int(cur["open_time"]),
            "trigger_level": trigger,
            "volume_ratio": float(fib["volume_ratio"]),
            "trend": trend,
            "trend_strength": strength,
            "fib_0618": float(fib["fib_0618"]),
            "fib_0786": float(fib["fib_0786"]),
            "swing_high": float(fib["swing_high"]),
            "swing_low": float(fib["swing_low"]),
            "reasons": ["FIB 0.618-0.786 pullback + potvrzené odmítnutí + 15m trend"],
        }

    _fixed.ENABLED_SETUPS = set(_fixed.ENABLED_SETUPS) | {"FIB_0618_0786"}
    _fixed.detect_signal = _fixed_detect_signal_with_fib

    _scanner_signal_for = _scanner.signal_for

    async def _scanner_signal_for_with_fib(client, row):
        base = await _scanner_signal_for(client, row)
        if base:
            return base
        symbol = row["symbol"]
        if symbol in _scanner.paper_positions:
            return None
        try:
            raw1, raw15 = await asyncio.gather(
                _scanner.klines(client, symbol, _scanner.ENTRY_INTERVAL, 60),
                _scanner.klines(client, symbol, "15m", 70),
            )
            m = [_scanner.c(x) for x in raw1][:-1]
            s = [_scanner.c(x) for x in raw15][:-1]
            if len(m) < 33 or len(s) < 52:
                return None
            conf = m[-1]
            fib = fib_pullback(
                [x["h"] for x in m], [x["l"] for x in m],
                [x["c"] for x in m], [x["v"] for x in m],
                lookback=30, min_impulse_pct=0.0045, min_volume_ratio=0.85,
            )
            if not fib:
                return None
            closes15 = [x["c"] for x in s]
            e20 = _scanner.ema(closes15, 20)
            e50 = _scanner.ema(closes15, 50)
            if not e20 or not e50:
                return None
            trend, trend_state, trend_strength = _scanner.classify_15m_trend(e20, e50, conf["c"])
            side = fib["signal"]
            if trend_state == "NEUTRAL" or side != trend:
                return None
            entry = float(conf["c"])
            trigger = entry * (0.9999 if side == "LONG" else 1.0001)
            if _scanner.last_entry_candle.get(symbol) == conf["t"]:
                return None
            return {
                "symbol": symbol,
                "side": side,
                "setup": "FIB_0618_0786",
                "entry": entry,
                "trigger_level": trigger,
                "trigger_extension": _scanner.trigger_extension(side, trigger, entry),
                "pattern_low": min(x["l"] for x in m[-4:]),
                "pattern_high": max(x["h"] for x in m[-4:]),
                "volume_ratio": float(fib["volume_ratio"]),
                "candle_body_ratio": _scanner.body(conf) / _scanner.rng(conf),
                "trend_strength": trend_strength,
                "trend": trend,
                "trend_state": trend_state,
                "trend_filter": "ALIGNED_15M_FIB",
                "strength": row["strength"],
                "strength_bucket": row["bucket"],
                "candle_time": conf["t"],
                "fib_0618": float(fib["fib_0618"]),
                "fib_0786": float(fib["fib_0786"]),
                "swing_high": float(fib["swing_high"]),
                "swing_low": float(fib["swing_low"]),
            }
        except Exception as exc:
            print("SCANNER FIB PATCH ERROR", symbol, repr(exc), flush=True)
            return None

    _scanner.signal_for = _scanner_signal_for_with_fib
    print("FIB_PATCH_ACTIVE fixed+scanner", flush=True)
except Exception as exc:
    print("SITECUSTOMIZE PATCH ERROR:", repr(exc), flush=True)
