"""Runtime bootstrap for V8.

If DATABASE_URL is not configured directly on the V8 Render service, retrieve it
from the authenticated V8.1 internal bridge before the FastAPI startup handler
runs. This keeps the database credential out of the public repository while
allowing V8 to use the same Render Postgres database and its existing
persistence code unchanged.
"""

import os
from functools import wraps

try:
    import httpx
    from fastapi import FastAPI

    _original_on_event = FastAPI.on_event

    def _patched_on_event(self, event_type):
        original_decorator = _original_on_event(self, event_type)

        def decorator(func):
            if event_type != "startup":
                return original_decorator(func)

            @wraps(func)
            async def startup_wrapper(*args, **kwargs):
                g = func.__globals__
                if not g.get("DATABASE_URL"):
                    bridge_url = os.getenv("V8_DB_BRIDGE_URL")
                    token = os.getenv("V8_DB_BRIDGE_TOKEN")
                    if bridge_url and token:
                        try:
                            async with httpx.AsyncClient(timeout=8.0) as client:
                                r = await client.get(
                                    bridge_url,
                                    headers={"X-Bridge-Token": token, "Cache-Control": "no-store"},
                                )
                                r.raise_for_status()
                                db_url = r.json().get("database_url")
                                if db_url:
                                    g["DATABASE_URL"] = db_url
                                    os.environ["DATABASE_URL"] = db_url
                                    print("V8 DATABASE BRIDGE CONNECTED")
                                else:
                                    print("V8 DATABASE BRIDGE ERROR: empty database_url")
                        except Exception as exc:
                            print("V8 DATABASE BRIDGE ERROR:", exc)
                return await func(*args, **kwargs)

            return original_decorator(startup_wrapper)

        return decorator

    FastAPI.on_event = _patched_on_event

except Exception as exc:
    print("V8 RUNTIME PATCH ERROR:", exc)
