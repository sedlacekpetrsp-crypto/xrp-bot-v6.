import os
import json
import asyncio
import time
from datetime import datetime, timezone, timedelta

import httpx
import psycopg
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response

# ============================================================
# V8 ADAPTIVE LIQUIDITY SCALPER — PAPER
# Stable build: pooled Binance client, cached dashboard,
# deduplicated signal logs, 429 backoff, lower request volume.
# ============================================================

app = FastAPI(title="V8 Adaptive Liquidity Scalper")

SYMBOLS = ["XRPUSDC", "ETHUSDC", "SOLUSDC"]
BINANCE_API = "https://data-api.binance.vision"
TRADING_MODE = "PAPER"
DATABASE_URL = os.getenv("DATABASE_URL")
STARTING_BALANCE = 10000.0

RISK_PER_TRADE = 0.0025
FEE_RATE = 0.0005
SLIPPAGE_RATE = 0.0002
ROUND_TRIP_COST = 2 * (FEE_RATE + SLIPPAGE_RATE)
MIN_EDGE_MULTIPLE = 1.50
MAX_TRADE_MINUTES = 12
LOOP_SECONDS = 15
DAILY_LOSS_LIMIT_R = 3.0
MAX_CONSECUTIVE_LOSSES = 3
LOSS_STREAK_COOLDOWN_MIN = 30

TREND_ADX_MIN = 19.0
RANGE_ADX_MAX = 15.0
EMA_SEP_MIN = 0.0009
MIN_SCORE = 6
SWEEP_LOOKBACK = 24
BREAKOUT_LOOKBACK = 20
MIN_SWEEP_WICK_ATR = 0.12
MIN_SWEEP_VOLUME = 1.05
MIN_BREAKOUT_VOLUME = 1.20
MIN_TREND_VOLUME = 0.90

ORDER_BOOK_LEVELS = 20
BOOK_SNAPSHOTS = 2
BOOK_DELAY = 0.35
BOOK_LONG_MIN = 0.535
BOOK_SHORT_MAX = 0.465
BOOK_MAX_SPREAD = 0.06

SETUP_PARAMS = {
    "LIQUIDITY_SWEEP": {"atr_mult": 0.95, "rr": 1.80},
    "TREND_PULLBACK": {"atr_mult": 1.00, "rr": 1.70},
    "BREAKOUT": {"atr_mult": 1.05, "rr": 1.90},
}
MIN_SETUP_TRADES_FOR_ADAPT = 12
MIN_SETUP_EXPECTANCY_R = -0.15

PAPER_BALANCE = STARTING_BALANCE
paper_position = None
trade_history = []
last_entry_candle = {}
cooldown_until = None
last_analysis = {}
last_signal_log_key = {}
price_cache = {}

bot_loop_started = False
bot_task = None
http_client = None
last_cycle_at = None
last_error = None
http_429_count = 0
started_at = datetime.now(timezone.utc)


def utcnow():
    return datetime.now(timezone.utc)


def get_db():
    return psycopg.connect(DATABASE_URL) if DATABASE_URL else None


def init_db():
    if not DATABASE_URL:
        print("DATABASE_URL není nastaveno - V8 nebude ukládat historii.")
        return
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS v8_trades (
                    id SERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    setup TEXT NOT NULL,
                    regime TEXT,
                    score INTEGER,
                    entry_price DOUBLE PRECISION NOT NULL,
                    exit_price DOUBLE PRECISION NOT NULL,
                    qty DOUBLE PRECISION NOT NULL,
                    gross_pnl DOUBLE PRECISION NOT NULL,
                    fees DOUBLE PRECISION NOT NULL,
                    pnl DOUBLE PRECISION NOT NULL,
                    initial_risk_usdc DOUBLE PRECISION,
                    mae_r DOUBLE PRECISION,
                    mfe_r DOUBLE PRECISION,
                    reason TEXT,
                    opened_at TIMESTAMPTZ,
                    closed_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS v8_state (
                    id INTEGER PRIMARY KEY,
                    state JSONB NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS v8_signals (
                    id SERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    candle_time BIGINT,
                    raw_signal TEXT,
                    setup TEXT,
                    regime TEXT,
                    score INTEGER,
                    decision TEXT,
                    reason TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
        conn.commit()


def save_state():
    if not DATABASE_URL:
        return
    state = {
        "paper_balance": PAPER_BALANCE,
        "paper_position": paper_position,
        "last_entry_candle": last_entry_candle,
        "cooldown_until": cooldown_until.isoformat() if cooldown_until else None,
    }
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO v8_state(id,state) VALUES(1,%s::jsonb)
                    ON CONFLICT(id) DO UPDATE SET state=EXCLUDED.state
                """, (json.dumps(state),))
            conn.commit()
    except Exception as e:
        print("SAVE STATE", e)


def load_state():
    global PAPER_BALANCE, paper_position, last_entry_candle, cooldown_until, trade_history
    if not DATABASE_URL:
        return
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT state FROM v8_state WHERE id=1")
                row = cur.fetchone()
                if row:
                    s = row[0] or {}
                    PAPER_BALANCE = float(s.get("paper_balance", STARTING_BALANCE))
                    paper_position = s.get("paper_position")
                    last_entry_candle = s.get("last_entry_candle", {}) or {}
                    cd = s.get("cooldown_until")
                    cooldown_until = datetime.fromisoformat(cd) if cd else None

                cur.execute("""
                    SELECT symbol,side,setup,regime,score,entry_price,exit_price,qty,
                           gross_pnl,fees,pnl,initial_risk_usdc,mae_r,mfe_r,reason,opened_at,closed_at
                    FROM v8_trades ORDER BY id DESC LIMIT 500
                """)
                trade_history = []
                for r in cur.fetchall():
                    trade_history.append({
                        "symbol": r[0], "side": r[1], "setup": r[2], "regime": r[3], "score": r[4],
                        "entry_price": r[5], "exit_price": r[6], "qty": r[7], "gross_pnl": r[8],
                        "fees": r[9], "pnl": r[10], "initial_risk_usdc": r[11], "mae_r": r[12],
                        "mfe_r": r[13], "reason": r[14],
                        "opened_at": r[15].isoformat() if r[15] else None,
                        "closed_at": r[16].isoformat() if r[16] else None,
                    })
    except Exception as e:
        print("LOAD STATE", e)


def save_trade(t):
    if not DATABASE_URL:
        return
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO v8_trades(
                    symbol,side,setup,regime,score,entry_price,exit_price,qty,
                    gross_pnl,fees,pnl,initial_risk_usdc,mae_r,mfe_r,reason,opened_at,closed_at
                ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                t["symbol"], t["side"], t["setup"], t.get("regime"), t.get("score"),
                t["entry_price"], t["exit_price"], t["qty"], t["gross_pnl"], t["fees"], t["pnl"],
                t.get("initial_risk_usdc"), t.get("mae_r"), t.get("mfe_r"), t["reason"],
                t["opened_at"], t["closed_at"]
            ))
        conn.commit()


def log_signal(a, decision, reason):
    if not DATABASE_URL:
        return
    key = (a.get("candle_time"), decision, a.get("raw_signal"), a.get("setup"), reason)
    symbol = a.get("symbol")
    if last_signal_log_key.get(symbol) == key:
        return
    last_signal_log_key[symbol] = key
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO v8_signals(symbol,candle_time,raw_signal,setup,regime,score,decision,reason)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    symbol, a.get("candle_time"), a.get("raw_signal"), a.get("setup"),
                    a.get("regime"), a.get("score"), decision, reason
                ))
            conn.commit()
    except Exception as e:
        print("SIGNAL LOG", e)


def ema(v, p):
    if len(v) < p:
        return None
    k = 2 / (p + 1)
    x = sum(v[:p]) / p
    for n in v[p:]:
        x = n * k + x * (1 - k)
    return x


def ema_series(v, p):
    if len(v) < p:
        return []
    k = 2 / (p + 1)
    out = [None] * (p - 1)
    x = sum(v[:p]) / p
    out.append(x)
    for n in v[p:]:
        x = n * k + x * (1 - k)
        out.append(x)
    return out


def rsi_wilder(v, p=14):
    if len(v) < p + 2:
        return None
    g, l = [], []
    for i in range(1, p + 1):
        ch = v[i] - v[i - 1]
        g.append(max(ch, 0))
        l.append(max(-ch, 0))
    ag, al = sum(g) / p, sum(l) / p
    for i in range(p + 1, len(v)):
        ch = v[i] - v[i - 1]
        ag = (ag * (p - 1) + max(ch, 0)) / p
        al = (al * (p - 1) + max(-ch, 0)) / p
    if al == 0:
        return 100.0
    rs = ag / al
    return 100 - 100 / (1 + rs)


def atr_wilder(h, l, c, p=14):
    if len(c) < p + 2:
        return None
    tr = [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, len(c))]
    a = sum(tr[:p]) / p
    for x in tr[p:]:
        a = (a * (p - 1) + x) / p
    return a


def adx_wilder(h, l, c, p=14):
    if len(c) < p * 2 + 2:
        return None
    tr, pd, md = [], [], []
    for i in range(1, len(c)):
        up = h[i] - h[i - 1]
        dn = l[i - 1] - l[i]
        pd.append(up if up > dn and up > 0 else 0)
        md.append(dn if dn > up and dn > 0 else 0)
        tr.append(max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])))
    ts, ps, ms = sum(tr[:p]), sum(pd[:p]), sum(md[:p])
    dx = []
    for i in range(p, len(tr)):
        ts = ts - ts / p + tr[i]
        ps = ps - ps / p + pd[i]
        ms = ms - ms / p + md[i]
        if ts <= 0:
            continue
        pdi, mdi = 100 * ps / ts, 100 * ms / ts
        dx.append(100 * abs(pdi - mdi) / (pdi + mdi) if pdi + mdi else 0)
    if not dx:
        return None
    a = sum(dx[:min(p, len(dx))]) / min(p, len(dx))
    for x in dx[p:]:
        a = (a * (p - 1) + x) / p
    return a


def macd_hist(v):
    e12, e26 = ema_series(v, 12), ema_series(v, 26)
    m = [e12[i] - e26[i] for i in range(len(v))
         if i < len(e12) and i < len(e26) and e12[i] is not None and e26[i] is not None]
    if len(m) < 11:
        return None, None
    s = ema(m, 9)
    sp = ema(m[:-1], 9)
    return m[-1] - s, m[-2] - sp if sp is not None else None


def vwap(h, l, c, v, n=120):
    n = min(n, len(c))
    vol = sum(v[-n:])
    if not vol:
        return None
    return sum(((a + b + d) / 3) * x for a, b, d, x in zip(h[-n:], l[-n:], c[-n:], v[-n:])) / vol


async def binance_get(path, params=None):
    global http_429_count, last_error
    if http_client is None:
        raise RuntimeError("HTTP client not initialized")
    delay = 1.0
    for attempt in range(4):
        try:
            r = await http_client.get(f"{BINANCE_API}{path}", params=params)
            if r.status_code == 429:
                http_429_count += 1
                retry_after = r.headers.get("Retry-After")
                try:
                    wait = float(retry_after) if retry_after else delay
                except ValueError:
                    wait = delay
                await asyncio.sleep(min(max(wait, 0.5), 10.0))
                delay *= 2
                continue
            r.raise_for_status()
            return r.json()
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            last_error = f"BINANCE {type(e).__name__}: {e}"
            if attempt == 3:
                raise
            await asyncio.sleep(delay)
            delay *= 2
    raise RuntimeError("Binance rate limit: retries exhausted")


async def get_klines(symbol, interval, limit=250):
    return await binance_get("/api/v3/klines", {
        "symbol": symbol, "interval": interval, "limit": limit
    })


async def get_live_price(symbol, max_age=2.0):
    cached = price_cache.get(symbol)
    now = time.monotonic()
    if cached and now - cached["ts"] <= max_age:
        return cached["price"]
    data = await binance_get("/api/v3/ticker/price", {"symbol": symbol})
    price = float(data["price"])
    price_cache[symbol] = {"price": price, "ts": now, "updated_at": utcnow().isoformat()}
    return price


async def book_snapshot(symbol):
    d = await binance_get("/api/v3/depth", {"symbol": symbol, "limit": ORDER_BOOK_LEVELS})
    b = sum(float(p) * float(q) for p, q in d.get("bids", []))
    a = sum(float(p) * float(q) for p, q in d.get("asks", []))
    return b / (a + b) if a + b else 0.5


async def persistent_book(symbol):
    vals = []
    for i in range(BOOK_SNAPSHOTS):
        vals.append(await book_snapshot(symbol))
        if i < BOOK_SNAPSHOTS - 1:
            await asyncio.sleep(BOOK_DELAY)
    return sum(vals) / len(vals), max(vals) - min(vals)


def setup_edge(setup, symbol):
    rows = [t for t in trade_history if t.get("setup") == setup and t.get("symbol") == symbol]
    if len(rows) < MIN_SETUP_TRADES_FOR_ADAPT:
        return True, None
    rs = [float(t["pnl"]) / float(t["initial_risk_usdc"])
          for t in rows if float(t.get("initial_risk_usdc") or 0) > 0]
    exp = sum(rs) / len(rs) if rs else None
    return exp is None or exp >= MIN_SETUP_EXPECTANCY_R, exp


def daily_risk_status():
    today = utcnow().date()
    rows = []
    for t in trade_history:
        try:
            if datetime.fromisoformat(t["closed_at"]).date() == today:
                rows.append(t)
        except Exception:
            pass
    pnl = sum(float(t["pnl"]) for t in rows)
    streak = 0
    for t in rows:
        if float(t["pnl"]) < 0:
            streak += 1
        else:
            break
    limit = max(PAPER_BALANCE, 1) * RISK_PER_TRADE * DAILY_LOSS_LIMIT_R
    return pnl, streak, pnl <= -limit, limit


async def strategy_analysis(symbol):
    k1, k5, book = await asyncio.gather(
        get_klines(symbol, "1m"),
        get_klines(symbol, "5m"),
        persistent_book(symbol)
    )
    a1, a5 = k1[:-1], k5[:-1]
    o = [float(x[1]) for x in a1]
    h = [float(x[2]) for x in a1]
    l = [float(x[3]) for x in a1]
    c = [float(x[4]) for x in a1]
    v = [float(x[5]) for x in a1]
    h5 = [float(x[2]) for x in a5]
    l5 = [float(x[3]) for x in a5]
    c5 = [float(x[4]) for x in a5]

    ct = int(a1[-1][0])
    hi, lo, cl = h[-1], l[-1], c[-1]
    e9, e21 = ema(c, 9), ema(c, 21)
    e20, e50 = ema(c5, 20), ema(c5, 50)
    rv = rsi_wilder(c)
    av = atr_wilder(h, l, c)
    ad = adx_wilder(h5, l5, c5)
    mh, mhp = macd_hist(c)
    vw = vwap(h, l, c, v)
    pv = v[-21:-1]
    vr = v[-1] / (sum(pv) / len(pv)) if pv and sum(pv) > 0 else 0
    bavg, bspread = book
    sep = abs(e20 - e50) / cl if cl and e20 is not None and e50 is not None else 0

    if ad is not None and ad >= TREND_ADX_MIN and sep >= EMA_SEP_MIN:
        regime = "TREND_LONG" if c5[-1] > e20 > e50 else "TREND_SHORT" if c5[-1] < e20 < e50 else "TRANSITION"
    elif ad is not None and ad <= RANGE_ADX_MAX:
        regime = "RANGE"
    else:
        regime = "TRANSITION"

    rng = max(hi - lo, 1e-12)
    bull = (cl - lo) / rng
    bear = (hi - cl) / rng
    ph = max(h[-SWEEP_LOOKBACK - 1:-1])
    pl = min(l[-SWEEP_LOOKBACK - 1:-1])

    sweep_high = hi > ph and cl < ph and (hi - ph) >= (av or 0) * MIN_SWEEP_WICK_ATR and bear >= 0.58 and vr >= MIN_SWEEP_VOLUME
    sweep_low = lo < pl and cl > pl and (pl - lo) >= (av or 0) * MIN_SWEEP_WICK_ATR and bull >= 0.58 and vr >= MIN_SWEEP_VOLUME

    bh = max(h[-BREAKOUT_LOOKBACK - 1:-1])
    bl = min(l[-BREAKOUT_LOOKBACK - 1:-1])
    mac_up = mh is not None and (mh > 0 or (mhp is not None and mh > mhp))
    mac_dn = mh is not None and (mh < 0 or (mhp is not None and mh < mhp))
    stable = bspread <= BOOK_MAX_SPREAD
    book_long = stable and bavg >= BOOK_LONG_MIN
    book_short = stable and bavg <= BOOK_SHORT_MAX

    ls = sum([
        e9 > e21, cl > e9, 40 <= rv <= 70, mac_up, bull >= 0.55,
        vr >= MIN_TREND_VOLUME, book_long, vw is not None and cl >= vw
    ])
    ss = sum([
        e9 < e21, cl < e9, 30 <= rv <= 60, mac_dn, bear >= 0.55,
        vr >= MIN_TREND_VOLUME, book_short, vw is not None and cl <= vw
    ])

    raw, setup, score = "WAIT", None, 0
    if sweep_low and bavg >= 0.50 and rv <= 58:
        raw, setup, score = "LONG", "LIQUIDITY_SWEEP", max(6, ls)
    elif sweep_high and bavg <= 0.50 and rv >= 42:
        raw, setup, score = "SHORT", "LIQUIDITY_SWEEP", max(6, ss)
    elif regime == "TREND_LONG" and lo <= max(e9, e21) * 1.0015 and cl > e9 and ls >= MIN_SCORE:
        raw, setup, score = "LONG", "TREND_PULLBACK", ls
    elif regime == "TREND_SHORT" and hi >= min(e9, e21) * 0.9985 and cl < e9 and ss >= MIN_SCORE:
        raw, setup, score = "SHORT", "TREND_PULLBACK", ss
    elif regime == "TREND_LONG" and cl > bh and vr >= MIN_BREAKOUT_VOLUME and ls >= MIN_SCORE:
        raw, setup, score = "LONG", "BREAKOUT", ls
    elif regime == "TREND_SHORT" and cl < bl and vr >= MIN_BREAKOUT_VOLUME and ss >= MIN_SCORE:
        raw, setup, score = "SHORT", "BREAKOUT", ss

    signal, reject, edge_pct = raw, None, 0.0
    if raw in ("LONG", "SHORT"):
        p = SETUP_PARAMS[setup]
        edge_pct = (av * p["atr_mult"] * p["rr"]) / cl
        if edge_pct < ROUND_TRIP_COST * MIN_EDGE_MULTIPLE:
            signal, reject = "WAIT", "EDGE_TOO_SMALL"
        enabled, exp = setup_edge(setup, symbol)
        if signal != "WAIT" and not enabled:
            signal, reject = "WAIT", f"SETUP_EXPECTANCY_{exp:.2f}R"
        if signal != "WAIT" and not stable:
            signal, reject = "WAIT", "BOOK_UNSTABLE"

    reason = f"{symbol} {regime} raw={raw} L/S={ls}/{ss} book={bavg:.3f} spread={bspread:.3f} vol={vr:.2f}x edge={edge_pct*100:.3f}%"
    if reject:
        reason += f" REJECT={reject}"

    return {
        "symbol": symbol, "signal": signal, "raw_signal": raw, "setup": setup, "score": score,
        "candle_time": ct, "regime": regime, "rsi": rv, "atr": av, "adx5": ad,
        "volume_ratio": vr, "book_imbalance": bavg, "book_spread": bspread,
        "long_score": ls, "short_score": ss, "sweep_high": sweep_high, "sweep_low": sweep_low,
        "liquidity_high": ph, "liquidity_low": pl, "expected_move_pct": edge_pct,
        "reason": reason
    }


def open_trade(a, price):
    global paper_position, last_entry_candle
    if paper_position or not a.get("atr"):
        return
    p = SETUP_PARAMS[a["setup"]]
    dist = float(a["atr"]) * p["atr_mult"]
    risk = PAPER_BALANCE * RISK_PER_TRADE
    qty = min(risk / dist, PAPER_BALANCE / price)
    side = a["signal"]
    if side == "LONG":
        entry = price * (1 + SLIPPAGE_RATE)
        sl = entry - dist
        tp = entry + dist * p["rr"]
    else:
        entry = price * (1 - SLIPPAGE_RATE)
        sl = entry + dist
        tp = entry - dist * p["rr"]

    paper_position = {
        "symbol": a["symbol"], "side": side, "setup": a["setup"],
        "regime": a["regime"], "score": a["score"], "entry_price": entry,
        "qty": qty, "stop_loss": sl, "take_profit": tp,
        "risk_distance": dist, "initial_risk_usdc": risk,
        "mae_r": 0.0, "mfe_r": 0.0, "breakeven_moved": False,
        "opened_at": utcnow().isoformat()
    }
    last_entry_candle[a["symbol"]] = a["candle_time"]
    save_state()
    log_signal(a, "ENTER", "accepted")
    print("OPEN V8", a["symbol"], side, a["setup"], entry)


def close_trade(price, reason):
    global PAPER_BALANCE, paper_position, cooldown_until, trade_history
    if not paper_position:
        return
    p = paper_position
    e, q = float(p["entry_price"]), float(p["qty"])
    if p["side"] == "LONG":
        x = price * (1 - SLIPPAGE_RATE)
        gross = (x - e) * q
    else:
        x = price * (1 + SLIPPAGE_RATE)
        gross = (e - x) * q

    fees = (e * q + x * q) * FEE_RATE
    net = gross - fees
    PAPER_BALANCE += net
    now = utcnow()
    t = {
        **p, "exit_price": x, "gross_pnl": gross, "fees": fees, "pnl": net,
        "reason": reason, "closed_at": now.isoformat()
    }
    save_trade(t)
    trade_history.insert(0, t)
    trade_history = trade_history[:500]

    _, streak, _, _ = daily_risk_status()
    cd = 2 if net < 0 else 0
    if net < 0 and streak >= MAX_CONSECUTIVE_LOSSES:
        cd = LOSS_STREAK_COOLDOWN_MIN
    cooldown_until = now + timedelta(minutes=cd)
    paper_position = None
    save_state()
    print("CLOSE V8", t["symbol"], reason, net)


async def manage_position():
    global paper_position
    if not paper_position:
        return
    p = paper_position
    price = await get_live_price(p["symbol"], max_age=1.0)
    e = float(p["entry_price"])
    d = float(p["risk_distance"])
    mr = (price - e) / d if p["side"] == "LONG" else (e - price) / d
    p["mfe_r"] = max(float(p.get("mfe_r", 0)), mr)
    p["mae_r"] = min(float(p.get("mae_r", 0)), mr)

    if not p.get("breakeven_moved") and mr >= 1.10:
        p["stop_loss"] = e * (1 + ROUND_TRIP_COST) if p["side"] == "LONG" else e * (1 - ROUND_TRIP_COST)
        p["breakeven_moved"] = True
        save_state()

    sl, tp = float(p["stop_loss"]), float(p["take_profit"])
    if p["side"] == "LONG":
        if price <= sl:
            close_trade(price, "BREAK EVEN" if p.get("breakeven_moved") else "STOP LOSS")
            return
        if price >= tp:
            close_trade(price, "TAKE PROFIT")
            return
    else:
        if price >= sl:
            close_trade(price, "BREAK EVEN" if p.get("breakeven_moved") else "STOP LOSS")
            return
        if price <= tp:
            close_trade(price, "TAKE PROFIT")
            return

    age = (utcnow() - datetime.fromisoformat(p["opened_at"])).total_seconds() / 60
    if age >= MAX_TRADE_MINUTES and (mr < 0.35 or age >= 18):
        close_trade(price, "TIME EXIT")


async def analyze_all():
    r = await asyncio.gather(*(strategy_analysis(s) for s in SYMBOLS), return_exceptions=True)
    out = []
    for s, x in zip(SYMBOLS, r):
        if isinstance(x, Exception):
            row = {"symbol": s, "signal": "ERROR", "raw_signal": "ERROR", "setup": None, "score": 0, "reason": str(x)}
        else:
            row = x
        last_analysis[s] = row
        out.append(row)
    return out


def choose_best(analyses):
    candidates = []
    for x in analyses:
        if x.get("raw_signal") in ("LONG", "SHORT") and x.get("signal") == "WAIT":
            log_signal(x, "REJECT", x.get("reason", "rejected"))
        if x.get("signal") not in ("LONG", "SHORT"):
            continue
        if last_entry_candle.get(x["symbol"]) == x.get("candle_time"):
            continue
        enabled, exp = setup_edge(x["setup"], x["symbol"])
        bonus = 0 if exp is None else max(-1, min(1, exp))
        rank = (
            2 if x["setup"] == "LIQUIDITY_SWEEP" else 1,
            int(x.get("score", 0)),
            bonus,
            float(x.get("adx5") or 0)
        )
        candidates.append((rank, x))
    if not candidates:
        return None
    candidates.sort(key=lambda z: z[0], reverse=True)
    return candidates[0][1]


async def cycle():
    global last_cycle_at, last_error
    try:
        await manage_position()
        if paper_position:
            last_cycle_at = utcnow().isoformat()
            return

        now = utcnow()
        if cooldown_until and now < cooldown_until:
            last_cycle_at = now.isoformat()
            return

        _, streak, blocked, _ = daily_risk_status()
        if blocked or streak >= MAX_CONSECUTIVE_LOSSES:
            last_cycle_at = now.isoformat()
            return

        analyses = await analyze_all()
        best = choose_best(analyses)
        if best:
            price = await get_live_price(best["symbol"], max_age=1.0)
            open_trade(best, price)
        last_cycle_at = utcnow().isoformat()
    except Exception as e:
        last_error = f"{type(e).__name__}: {e}"
        print("V8 CYCLE", e)


async def loop():
    while True:
        await cycle()
        await asyncio.sleep(LOOP_SECONDS)


def stats():
    n = len(trade_history)
    w = sum(1 for t in trade_history if float(t["pnl"]) > 0)
    pnl = sum(float(t["pnl"]) for t in trade_history)
    fees = sum(float(t["fees"]) for t in trade_history)
    gp = sum(float(t["pnl"]) for t in trade_history if float(t["pnl"]) > 0)
    gl = abs(sum(float(t["pnl"]) for t in trade_history if float(t["pnl"]) < 0))
    pf = gp / gl if gl else (999 if gp else 0)
    return {
        "count": n, "wins": w, "win_rate": w / n * 100 if n else 0,
        "total_pnl": pnl, "fees": fees, "profit_factor": pf
    }


@app.on_event("startup")
async def startup():
    global bot_loop_started, bot_task, http_client, started_at
    started_at = utcnow()
    limits = httpx.Limits(max_connections=10, max_keepalive_connections=5, keepalive_expiry=30.0)
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0), limits=limits, headers={"User-Agent": "xrp-bot-v8/1.1"})
    init_db()
    load_state()
    if not bot_loop_started:
        bot_loop_started = True
        bot_task = asyncio.create_task(loop())
        print("XRP BOT V8 STABLE STARTED")


@app.on_event("shutdown")
async def shutdown():
    global bot_task, http_client
    if bot_task:
        bot_task.cancel()
    if http_client:
        await http_client.aclose()
        http_client = None


@app.get("/analyze")
async def analyze():
    unrealized = 0.0
    if paper_position:
        cached = price_cache.get(paper_position["symbol"])
        if cached:
            p = paper_position
            price = cached["price"]
            e, q = float(p["entry_price"]), float(p["qty"])
            unrealized = (price - e) * q if p["side"] == "LONG" else (e - price) * q

    pnl_today, streak, blocked, limit = daily_risk_status()
    return {
        "bot": "V8 Adaptive Liquidity Scalper",
        "mode": TRADING_MODE,
        "symbols": SYMBOLS,
        "paper_balance": PAPER_BALANCE,
        "equity": PAPER_BALANCE + unrealized,
        "unrealized_pnl": unrealized,
        "position": paper_position,
        "market": last_analysis,
        "stats": stats(),
        "trade_history": trade_history[:50],
        "risk_status": {
            "today_pnl": pnl_today,
            "loss_streak": streak,
            "blocked": blocked,
            "daily_loss_limit": limit
        },
        "last_cycle_at": last_cycle_at,
        "last_error": last_error,
        "http_429_count": http_429_count,
        "min_edge_multiple": MIN_EDGE_MULTIPLE,
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "bot": "V8 Adaptive Liquidity Scalper",
        "mode": TRADING_MODE,
        "loop_started": bot_loop_started,
        "last_cycle_at": last_cycle_at,
        "position_open": bool(paper_position),
        "http_429_count": http_429_count,
        "last_error": last_error,
        "uptime_seconds": int((utcnow() - started_at).total_seconds()),
    }


@app.head("/")
@app.head("/analyze")
@app.head("/health")
async def uptime_head():
    return Response(status_code=200)


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
<!doctype html>
<html lang="cs"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bot V8</title>
<style>
body{margin:0;background:#0b1118;color:#eef4f8;font-family:Arial,sans-serif}.wrap{max-width:1050px;margin:auto;padding:14px}
.card{background:#151c24;border:1px solid #26313d;border-radius:16px;padding:16px;margin-bottom:12px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}.coin{background:#10171f;border-radius:12px;padding:12px}
.row{display:flex;justify-content:space-between;gap:12px;margin:6px 0}.green{color:#5ce68b}.red{color:#ff6b6b}.yellow{color:#ffd166}.muted{opacity:.65}
.trade{display:grid;grid-template-columns:1.1fr .8fr 1fr 1fr;gap:8px;padding:9px 0;border-bottom:1px solid #29343e;font-size:13px}
h1{font-size:24px;margin:0 0 8px}h2{font-size:18px}
</style></head><body><div class="wrap">
<div class="card"><h1>⚡ BOT V8 ADAPTIVE LIQUIDITY SCALPER</h1><div class="muted">PAPER • pooled Binance client • cached dashboard</div></div>
<div class="card"><div id="stats" class="grid"></div></div>
<div class="card"><h2>📡 Trhy</h2><div id="coins" class="grid"></div></div>
<div class="card"><h2>📌 Otevřená pozice</h2><div id="position" class="muted">—</div></div>
<div class="card"><h2>🧾 Posledních 50 obchodů</h2><div id="trades"></div></div>
<div class="card muted" id="health">Načítám…</div>
</div><script>
const f=(n,d=2)=>Number(n||0).toFixed(d);
async function refresh(){
 try{
  const r=await fetch('/analyze',{cache:'no-store'}),d=await r.json(),s=d.stats||{};
  document.getElementById('stats').innerHTML=[
   ['Balance',f(d.paper_balance,2)+' USDC'],['Equity',f(d.equity,2)+' USDC'],['Obchody',s.count||0],
   ['Win rate',f(s.win_rate,1)+' %'],['PnL',f(s.total_pnl,2)+' USDC'],['Fees',f(s.fees,2)+' USDC']
  ].map(x=>`<div class="coin"><div class="muted">${x[0]}</div><b>${x[1]}</b></div>`).join('');
  document.getElementById('coins').innerHTML=Object.values(d.market||{}).map(x=>{
   const sig=x.signal||'WAIT',cls=sig==='LONG'?'green':sig==='SHORT'?'red':'yellow';
   return `<div class="coin"><b>${x.symbol}</b><div class="row"><span>Signál</span><b class="${cls}">${sig}</b></div>
   <div class="row"><span>Raw</span><span>${x.raw_signal||'WAIT'}</span></div><div class="row"><span>Setup</span><span>${x.setup||'—'}</span></div>
   <div class="row"><span>Score L/S</span><span>${x.long_score??'—'} / ${x.short_score??'—'}</span></div>
   <div class="muted">${x.reason||''}</div></div>`;
  }).join('');
  const p=d.position; document.getElementById('position').innerHTML=p?`<b>${p.symbol} ${p.side}</b> • entry ${f(p.entry_price,6)} • SL ${f(p.stop_loss,6)} • TP ${f(p.take_profit,6)} • uPnL ${f(d.unrealized_pnl,2)}`:'Žádná otevřená pozice';
  document.getElementById('trades').innerHTML=(d.trade_history||[]).map(t=>`<div class="trade"><span>${t.symbol}</span><span>${t.side}</span><span>${t.reason}</span><span class="${Number(t.pnl)>=0?'green':'red'}">${f(t.pnl,2)}</span></div>`).join('')||'<div class="muted">Zatím bez obchodů.</div>';
  document.getElementById('health').textContent=`Cyklus: ${d.last_cycle_at||'—'} • 429: ${d.http_429_count||0} • edge ×${d.min_edge_multiple} • chyba: ${d.last_error||'žádná'}`;
 }catch(e){document.getElementById('health').textContent='Dashboard error: '+e}
}
refresh();setInterval(refresh,10000);
</script></body></html>
"""
