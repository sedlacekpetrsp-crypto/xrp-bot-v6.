#!/usr/bin/env python3
"""
Audit DISTINCT public BTC signal sequences from BlueWhaleCryptoTrading.

Uses Telegram public HTML timestamps (UTC), public SL text and Binance 1m data.
Exact VIP entry/TP are NOT invented. We use the Binance close at the first
public signal timestamp as a clearly labelled proxy entry.

Repeated identical SL posts inside 72h are treated as updates/reposts of the
same signal cluster, not separate trades.

Direction is inferred only when the SL band is clearly below/above proxy price:
- stop band below proxy -> LONG
- stop band above proxy -> SHORT
otherwise UNKNOWN.

Each cluster ends at the first of:
- next distinct SL cluster
- 72h after first signal

This script reports:
- whether the masked stop band was definitely hit / definitely not hit / ambiguous
- max favorable/adverse move from public-post proxy entry
- proxy close-to-close return at cluster end
- nearby public result/update posts between start and end
"""
from __future__ import annotations
import json, re, time, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta
from html import unescape

TG = "https://t.me/s/BlueWhaleCryptoTrading"
BINANCE = "https://data-api.binance.vision/api/v3/klines"
UA = "Mozilla/5.0 (compatible; BlueWhaleSequenceAudit/1.0)"
MAX_PAGES = 20

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")

def clean_html(s):
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = unescape(s)
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r"\n\s+", "\n", s)
    return s.strip()

def collect():
    seen={}
    before=None
    for _ in range(MAX_PAGES):
        url = TG if before is None else TG+"?"+urllib.parse.urlencode({"before":before})
        html=fetch(url)
        chunks=re.split(r'(?=<div class="tgme_widget_message_wrap)',html)
        posts=[]
        for ch in chunks:
            m=re.search(r'data-post="BlueWhaleCryptoTrading/(\d+)"',ch)
            if not m: continue
            mid=int(m.group(1))
            dtm=re.search(r'<time[^>]+datetime="([^"]+)"',ch)
            tm=re.search(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>',ch,flags=re.S)
            txt=clean_html(tm.group(1)) if tm else ""
            posts.append({"id":mid,"dt":dtm.group(1) if dtm else None,"text":txt})
        if not posts: break
        for p in posts: seen[p["id"]]=p
        oldest=min(p["id"] for p in posts)
        if before is not None and oldest>=before: break
        before=oldest
        time.sleep(0.15)
    return [seen[k] for k in sorted(seen)]

def parse_stop(text):
    u=text.upper().replace("$","")
    # Examples: 68,6xx ; 75,8xx ; 78,4xx ; 80,0xx ; 748xx ; 76xxx ; 79,000
    m=re.search(r'\bSL\s*[:=]?\s*([0-9]{2,3}(?:,[0-9]{1,3})?(?:X{2,3})?)',u)
    if not m: return None
    raw=m.group(1).replace(",","")
    if "X" not in raw:
        try:
            v=float(raw)
            return {"raw":m.group(1),"low":v,"high":v}
        except: return None
    n=raw.count("X")
    prefix=raw[:-n]
    if not prefix.isdigit(): return None
    base=int(prefix)*(10**n)
    return {"raw":m.group(1),"low":float(base),"high":float(base+(10**n)-1)}

def dtparse(s): return datetime.fromisoformat(s.replace("Z","+00:00"))
def ms(x): return int(x.timestamp()*1000)

def fetch_1m(start,end):
    out=[]; cur=ms(start); endms=ms(end)
    while cur<endms:
        q=urllib.parse.urlencode({"symbol":"BTCUSDT","interval":"1m","startTime":cur,"endTime":endms,"limit":1000})
        req=urllib.request.Request(BINANCE+"?"+q,headers={"User-Agent":UA})
        with urllib.request.urlopen(req,timeout=30) as r:
            rows=json.loads(r.read().decode())
        if not rows: break
        out.extend(rows)
        nxt=int(rows[-1][0])+1
        if nxt<=cur: break
        cur=nxt
        time.sleep(0.02)
    return out

def is_btc(text): return "BTC" in text.upper()
def is_resultish(text):
    u=text.upper()
    return any(k in u for k in ["PROFIT","HIT TP","RESULT","STILL HOLDING","PLAN UPDATE","BIG GIFT","BIG PROFIT"])

def main():
    posts=collect()
    sigs=[]
    for p in posts:
        if not p["dt"] or not is_btc(p["text"]): continue
        st=parse_stop(p["text"])
        if st: sigs.append({**p,"stop":st})

    # Deduplicate repeated same stop band within 72h.
    clusters=[]
    for s in sigs:
        t=dtparse(s["dt"])
        matched=None
        for c in reversed(clusters):
            if c["stop"]["low"]==s["stop"]["low"] and c["stop"]["high"]==s["stop"]["high"]:
                if t-dtparse(c["first"]["dt"]) <= timedelta(hours=72):
                    matched=c
                    break
        if matched:
            matched["reposts"].append(s)
        else:
            clusters.append({"first":s,"stop":s["stop"],"reposts":[]})

    audits=[]
    for i,c in enumerate(clusters):
        start=dtparse(c["first"]["dt"])
        natural_end=start+timedelta(hours=72)
        if i+1<len(clusters):
            nxt=dtparse(clusters[i+1]["first"]["dt"])
            end=min(natural_end,nxt)
        else:
            end=natural_end

        rows=fetch_1m(start-timedelta(minutes=1),end+timedelta(minutes=1))
        if not rows: continue
        first=min(rows,key=lambda x:abs(int(x[0])-ms(start)))
        entry=float(first[4])
        hi=max(float(x[2]) for x in rows if ms(start)<=int(x[0])<=ms(end))
        lo=min(float(x[3]) for x in rows if ms(start)<=int(x[0])<=ms(end))
        last=min(rows,key=lambda x:abs(int(x[0])-ms(end)))
        end_close=float(last[4])

        sl=c["stop"]
        if sl["high"] < entry*0.995:
            side="LONG"
            if lo<=sl["low"]: stop_status="DEFINITELY_HIT"
            elif lo>sl["high"]: stop_status="DEFINITELY_NOT_HIT"
            else: stop_status="AMBIGUOUS_MASK"
            mfe=(hi/entry-1)*100
            mae=(lo/entry-1)*100
            endret=(end_close/entry-1)*100
        elif sl["low"] > entry*1.005:
            side="SHORT"
            if hi>=sl["high"]: stop_status="DEFINITELY_HIT"
            elif hi<sl["low"]: stop_status="DEFINITELY_NOT_HIT"
            else: stop_status="AMBIGUOUS_MASK"
            mfe=(entry/lo-1)*100
            mae=(entry/hi-1)*100
            endret=(entry/end_close-1)*100
        else:
            side="UNKNOWN"
            stop_status="DIRECTION_UNCLEAR"
            mfe=mae=endret=None

        related=[]
        for p in posts:
            if not p["dt"] or not is_btc(p["text"]): continue
            tp=dtparse(p["dt"])
            if start < tp <= end and is_resultish(p["text"]) and parse_stop(p["text"]) is None:
                related.append({"id":p["id"],"dt":p["dt"],"text":p["text"][:240]})

        audits.append({
            "signal_id":c["first"]["id"],
            "signal_dt":c["first"]["dt"],
            "signal_text":c["first"]["text"],
            "stop":sl,
            "repost_count":len(c["reposts"]),
            "cluster_end_dt":end.isoformat(),
            "proxy_entry":entry,
            "inferred_side":side,
            "stop_status":stop_status,
            "window_high":hi,
            "window_low":lo,
            "max_favorable_pct":mfe,
            "max_adverse_pct":mae,
            "proxy_end_return_pct":endret,
            "related_public_updates_or_results":related[:10],
        })

    recent=[a for a in audits if dtparse(a["signal_dt"])>=datetime(2026,8,1,tzinfo=timezone.utc)]
    summary={
        "distinct_signal_clusters_total":len(audits),
        "recent_since_2026_08_01":len(recent),
        "recent_definitely_not_stopped":sum(a["stop_status"]=="DEFINITELY_NOT_HIT" for a in recent),
        "recent_definitely_stopped":sum(a["stop_status"]=="DEFINITELY_HIT" for a in recent),
        "recent_ambiguous":sum(a["stop_status"] in ("AMBIGUOUS_MASK","DIRECTION_UNCLEAR") for a in recent),
        "recent_audits":recent,
        "note":"Proxy entry = Binance 1m close at first public signal timestamp; exact VIP entry/TP not claimed.",
    }
    print("RESULT_JSON="+json.dumps(summary,ensure_ascii=False,sort_keys=True),flush=True)

if __name__=="__main__":
    main()
