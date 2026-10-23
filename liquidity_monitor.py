"""In-process status: no dependency on a separate Render service."""
import liquidity_local

def snapshot():
    out = liquidity_local.snapshot()
    out.update(status_available=bool(liquidity_local.runtime.get('state')),
               status_fresh=out['healthy'], connection_error=out['last_error'],
               risk_per_trade_pct=out['risk_pct'], atr_stop_mult=out['stop_atr'])
    # Preserve dashboard schema used by the formerly remote V2 endpoint.
    out['positions'] = {p['symbol']: p for p in out['positions']}
    out['analysis'] = {'XRPUSDT': out['analysis']} if out['analysis'] else {}
    return out

def install(app, core):
    liquidity_local.install(app, core, local_only=True)
