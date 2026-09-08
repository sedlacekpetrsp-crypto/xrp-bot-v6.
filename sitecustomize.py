"""Runtime compatibility and secure DB bridge for V8.1.

- Keeps explicit HEAD routes for uptime checks.
- Keeps up to 50 trades in /analyze and dashboard.
- Adds an authenticated internal endpoint that exposes DATABASE_URL only to V8
  when the shared secret header matches V8_DB_BRIDGE_TOKEN.
"""

import os

try:
    from functools import wraps
    from fastapi import FastAPI, Header, HTTPException

    _original_get = FastAPI.get
    _bridge_registered = False

    def _patched_get(self, path, *args, **kwargs):
        global _bridge_registered
        original_decorator = _original_get(self, path, *args, **kwargs)

        def decorator(func):
            endpoint = func

            if path == "/analyze":
                @wraps(func)
                async def analyze_wrapper(*f_args, **f_kwargs):
                    result = await func(*f_args, **f_kwargs)
                    if isinstance(result, dict):
                        history = func.__globals__.get("trade_history", [])
                        result["trade_history"] = history[:50]
                    return result
                endpoint = analyze_wrapper

            elif path == "/":
                @wraps(func)
                async def dashboard_wrapper(*f_args, **f_kwargs):
                    html = await func(*f_args, **f_kwargs)
                    if isinstance(html, str):
                        html = html.replace("Posledních 20 obchodů", "Posledních 50 obchodů")
                        html = html.replace("slice(0,20)", "slice(0,50)")
                    return html
                endpoint = dashboard_wrapper

            registered = original_decorator(endpoint)

            if path in ("/", "/analyze", "/health"):
                async def head_ok():
                    return None
                self.add_api_route(
                    path,
                    head_ok,
                    methods=["HEAD"],
                    include_in_schema=False,
                    status_code=200,
                )

            if not _bridge_registered:
                _bridge_registered = True

                async def db_bridge(x_bridge_token: str | None = Header(default=None)):
                    expected = os.getenv("V8_DB_BRIDGE_TOKEN")
                    database_url = os.getenv("DATABASE_URL")
                    if not expected or not x_bridge_token or x_bridge_token != expected:
                        raise HTTPException(status_code=404, detail="Not found")
                    if not database_url:
                        raise HTTPException(status_code=503, detail="Database unavailable")
                    return {"database_url": database_url}

                self.add_api_route(
                    "/_internal/v8-db-bridge",
                    db_bridge,
                    methods=["GET"],
                    include_in_schema=False,
                )

            return registered

        return decorator

    FastAPI.get = _patched_get

except Exception as exc:
    print("V8.1 RUNTIME PATCH ERROR:", exc)
