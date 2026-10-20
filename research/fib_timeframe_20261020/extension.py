import asyncio,gzip,json,pathlib,sys
from run import Replay,HERE,P,ms
async def main():
 r=Replay(pathlib.Path(sys.argv[1]));signals,diag=await r.signals('1h');out={'diagnostics':diag};trades={}
 for period in ('development','holdout'):
  out[period],trades[period]=r.run(signals,*map(ms,P[period]),P['slippage_per_side'])
 out['stress'],trades['stress']=r.run(signals,*map(ms,P['holdout']),P['stress_slippage_per_side'])
 (HERE/'extension_results.json').write_text(json.dumps(out,indent=2))
 (HERE/'extension_trades.json.gz').write_bytes(gzip.compress(json.dumps(trades,separators=(',',':')).encode()))
 print(json.dumps(out),flush=True)
asyncio.run(main())
