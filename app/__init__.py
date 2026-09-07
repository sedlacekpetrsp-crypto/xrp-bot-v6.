"""V8.1 ASGI compatibility wrapper.

Render starts `uvicorn app:app`.  Because this package is preferred over the
legacy app.py module, we load the existing bot unchanged and only add explicit
HEAD endpoints required by UptimeRobot.
"""
from pathlib import Path
import importlib.util

_legacy_path = Path(__file__).resolve().parent.parent / "app.py"
_spec = importlib.util.spec_from_file_location("v81_legacy_app", _legacy_path)
_legacy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_legacy)

app = _legacy.app

@app.head("/", include_in_schema=False)
async def uptime_head_root():
    return None

@app.head("/analyze", include_in_schema=False)
async def uptime_head_analyze():
    return None

@app.head("/health", include_in_schema=False)
async def uptime_head_health():
    return None
