"""Compatibility patch for uptime monitors.

UptimeRobot checks the service root with HTTP HEAD. The app has GET / but no
HEAD / route, so FastAPI returns 405 even while the bot is healthy. Patch the
FastAPI ASGI entry point so HEAD / is handled as GET /. Trading logic is
untouched.
"""

try:
    from fastapi import FastAPI

    _original_call = FastAPI.__call__

    async def _uptime_head_compatible_call(self, scope, receive, send):
        if (
            scope.get("type") == "http"
            and scope.get("method") == "HEAD"
            and scope.get("path") == "/"
        ):
            scope = dict(scope)
            scope["method"] = "GET"
        return await _original_call(self, scope, receive, send)

    FastAPI.__call__ = _uptime_head_compatible_call
except Exception as exc:
    print("UPTIME HEAD PATCH ERROR:", exc)
