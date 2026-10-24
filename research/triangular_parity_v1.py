"""Causal BTC-ETH-USDT triangular parity execution model."""
from dataclasses import dataclass, replace
from math import isfinite

BAR_MS = 300_000


@dataclass(frozen=True)
class Config:
    minimum_gross_dislocation: float = 0.0050
    cooldown_bars: int = 12
    position_fraction: float = 0.20
    fee_rate: float = 0.00095
    slippage_rate: float = 0.00020
    initial_equity: float = 10_000.0


def validate(bars):
    stamps=[]
    for bar in bars:
        values=[bar[k] for k in ("btcusdt_open","btcusdt_close","ethusdt_open","ethusdt_close","ethbtc_open","ethbtc_close")]
        if not all(isfinite(value) and value>0 for value in values): raise ValueError("Invalid synchronized prices")
        if bar["timestamp"]%BAR_MS: raise ValueError("Invalid timestamp")
        stamps.append(bar["timestamp"])
    if any(stamps[i]<=stamps[i-1] for i in range(1,len(stamps))): raise ValueError("Unordered bars")


def dislocations(bar, field="close"):
    btc=bar[f"btcusdt_{field}"]; eth=bar[f"ethusdt_{field}"]; cross=bar[f"ethbtc_{field}"]
    forward=eth/(btc*cross)-1
    reverse=(btc*cross)/eth-1
    return forward,reverse


def execute_cycle(bar, route, notional, config=Config()):
    fee=1-config.fee_rate; slip=config.slippage_rate
    btc=bar["btcusdt_open"]; eth=bar["ethusdt_open"]; cross=bar["ethbtc_open"]
    if route=="USDT_BTC_ETH_USDT":
        btc_amount=notional/(btc*(1+slip))*fee
        eth_amount=btc_amount/(cross*(1+slip))*fee
        final=eth_amount*eth*(1-slip)*fee
    elif route=="USDT_ETH_BTC_USDT":
        eth_amount=notional/(eth*(1+slip))*fee
        btc_amount=eth_amount*cross*(1-slip)*fee
        final=btc_amount*btc*(1-slip)*fee
    else: raise ValueError("Unknown route")
    return final


def backtest(bars,start_ts,end_ts,config=Config()):
    validate(bars); equity=config.initial_equity; peak=equity; max_drawdown=0.0; cooldown_until=start_ts; trades=[]
    for i,bar in enumerate(bars):
        ts=bar["timestamp"]
        if ts<start_ts: continue
        if ts>=end_ts: break
        if ts>=cooldown_until and i>0 and ts-bars[i-1]["timestamp"]==BAR_MS:
            forward,reverse=dislocations(bars[i-1])
            best=max(forward,reverse)
            if best>=config.minimum_gross_dislocation:
                route="USDT_BTC_ETH_USDT" if forward>=reverse else "USDT_ETH_BTC_USDT"
                before=equity; notional=equity*config.position_fraction; final=execute_cycle(bar,route,notional,config)
                net=final-notional; equity+=net
                open_forward,open_reverse=dislocations(bar,"open")
                route_execution=open_forward if route=="USDT_BTC_ETH_USDT" else open_reverse
                trades.append({"signal_ts":bars[i-1]["timestamp"],"execution_ts":ts,"route":route,
                               "signal_dislocation":best,"execution_dislocation":route_execution,
                               "notional":notional,"net_pnl":net,"return_on_equity":net/before})
                cooldown_until=ts+config.cooldown_bars*BAR_MS
        peak=max(peak,equity); max_drawdown=max(max_drawdown,(peak-equity)/peak)
    return {"trades":trades,"ending_equity":equity,"net_return":equity/config.initial_equity-1,"max_drawdown":max_drawdown}


def with_cost_stress(config=Config()):
    return replace(config,fee_rate=config.fee_rate*2,slippage_rate=config.slippage_rate*2)
