"""Fibonacci 0.618-0.786 pullback setup for the integrated Fly engine.
Detects a completed impulse and confirmed rejection from the retracement zone.
Also installs a narrow startup hook so the current V8 Fly layer can be patched
with the no-momentum-flip exit policy without changing the combined app.
"""

import builtins
import sys


def fib_pullback(highs, lows, closes, volumes, lookback=24, min_impulse_pct=0.006, min_volume_ratio=0.85):
    if min(len(highs),len(lows),len(closes),len(volumes)) < lookback+3: return None
    h=list(map(float,highs)); l=list(map(float,lows)); c=list(map(float,closes)); v=list(map(float,volumes))
    start=max(0,len(c)-lookback-2); end=len(c)-1; sh=h[start:end]; sl=l[start:end]
    hi=max(sh); lo=min(sl); hi_i=start+sh.index(hi); lo_i=start+sl.index(lo)
    price=c[-1]; prev=c[-2]; base=sum(v[-21:-1])/max(len(v[-21:-1]),1); vr=v[-1]/base if base>0 else 0.0
    if lo_i<hi_i and (hi-lo)/max(lo,1e-12)>=min_impulse_pct:
        f618=hi-(hi-lo)*.618; f786=hi-(hi-lo)*.786
        if l[-1]<=f618 and h[-1]>=f786 and price>=f618 and price>prev and vr>=min_volume_ratio:
            return {'signal':'LONG','setup':'FIB_0618_0786','fib_0618':f618,'fib_0786':f786,'swing_high':hi,'swing_low':lo,'volume_ratio':vr}
    if hi_i<lo_i and (hi-lo)/max(hi,1e-12)>=min_impulse_pct:
        f618=lo+(hi-lo)*.618; f786=lo+(hi-lo)*.786
        if h[-1]>=f618 and l[-1]<=f786 and price<=f618 and price<prev and vr>=min_volume_ratio:
            return {'signal':'SHORT','setup':'FIB_0618_0786','fib_0618':f618,'fib_0786':f786,'swing_high':hi,'swing_low':lo,'volume_ratio':vr}
    return None


# sitecustomize imports fib_strategy before app_v8_candle_scanner imports
# v8_fly_layer. Wrap that one import only, then restore the normal importer.
if not getattr(builtins, "_v8_no_flip_import_hook", False):
    _normal_import = builtins.__import__

    def _v8_import(name, globals=None, locals=None, fromlist=(), level=0):
        module = _normal_import(name, globals, locals, fromlist, level)
        if name == "v8_fly_layer":
            target = sys.modules.get("v8_fly_layer")
            if target is not None and hasattr(target, "install") and not getattr(target, "_no_flip_install_wrapped", False):
                original_install = target.install

                def install_with_no_flip(bot_module):
                    original_install(bot_module)
                    from v8_fly_no_flip import patch
                    patch(bot_module)

                target.install = install_with_no_flip
                target._no_flip_install_wrapped = True
                builtins.__import__ = _normal_import
                print("V8_NO_FLIP_IMPORT_HOOK_READY", flush=True)
        return module

    builtins.__import__ = _v8_import
    builtins._v8_no_flip_import_hook = True
