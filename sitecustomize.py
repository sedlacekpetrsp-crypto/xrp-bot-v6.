import copy

try:
    import httpx
    import market_data
    from fastapi.responses import JSONResponse, Response

    _original_install_data_health = market_data.install_data_health

    def _patched_install_data_health(app):
        _original_install_data_health(app)

        if getattr(app, "title", "") != "V8 Candle Combined":
            return

        @app.middleware("http")
        async def _combined_live_price_middleware(request, call_next):
            # Only the public Combined dashboard gets the fast price layer.
            # Trading scans, entries, risk, SL/TP and persistence stay unchanged.
            if request.url.path == "/analyze":
                try:
                    import app_v8_candle_scanner as combined

                    fixed_data = copy.deepcopy(combined.snapshot("fixed"))
                    scanner_data = copy.deepcopy(combined.snapshot("scanner"))

                    async with httpx.AsyncClient(timeout=10) as client:
                        fp = fixed_data.get("position")
                        if fp:
                            px = await combined.fixed.get_live_price(client)
                            fixed_data["price"] = px
                            upnl = combined.fixed.unrealized(px)
                            fixed_data["unrealized_pnl"] = upnl
                            fixed_data["equity"] = float(fixed_data.get("balance", 0.0)) + upnl
                            fixed_data["time"] = combined.utcnow().isoformat()

                        sp = scanner_data.get("position")
                        if sp:
                            symbol = sp.get("symbol") or scanner_data.get("symbol") or "XRPUSDT"
                            px = await combined.scanner.price(client, symbol)
                            scanner_data["price"] = px
                            upnl = combined.scanner.est_net_unit(
                                sp["side"], float(sp["entry_price"]), px
                            ) * float(sp["qty"])
                            scanner_data["unrealized_pnl"] = upnl
                            scanner_data["equity"] = float(scanner_data.get("balance", 0.0)) + upnl
                            scanner_data["time"] = combined.utcnow().isoformat()

                    payload = {
                        "fixed": fixed_data,
                        "scanner": scanner_data,
                        "monitoring": combined.runtime_status(),
                        "time": combined.utcnow().isoformat(),
                        "live_price_refresh_seconds": 3,
                    }
                    return JSONResponse(payload, headers={"Cache-Control": "no-store"})
                except Exception as exc:
                    print("COMBINED LIVE PRICE FALLBACK:", repr(exc), flush=True)
                    # If the fresh quote is temporarily unavailable, use the bot's
                    # normal endpoint rather than breaking the dashboard.

            response = await call_next(request)

            if request.url.path == "/" and response.headers.get("content-type", "").startswith("text/html"):
                body = b"".join([chunk async for chunk in response.body_iterator])
                text = body.decode("utf-8")
                text = text.replace("setInterval(go,15000)", "setInterval(go,3000)")
                headers = dict(response.headers)
                headers.pop("content-length", None)
                headers["Cache-Control"] = "no-store"
                return Response(
                    content=text,
                    status_code=response.status_code,
                    headers=headers,
                    media_type="text/html",
                )

            return response

    market_data.install_data_health = _patched_install_data_health
except Exception as exc:
    print("SITECUSTOMIZE LIVE PRICE PATCH ERROR:", repr(exc), flush=True)
