#!/usr/bin/env python3
"""
Build a structured evidence pack from ACTUAL public Blue Whale BTC signal posts.

For each distinct SL cluster:
- OCR the FIRST public signal post (largest public images);
- extract exact-looking entry from labels such as Entry Price / Avg entry / Entry:;
- compare that entry with Binance BTCUSDT 1m price at the post timestamp;
- infer direction from explicit LONG/SHORT, otherwise from SL vs entry;
- OCR public follow-up/result posts for up to 72h and extract Close/Filled prices;
- if no exact close is public, report stop status + MFE/MAE instead of inventing an exit.

This is evidence collection, not a claim about VIP performance.
"""
from __future__ import annotations
import io, json, math, re, time, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta
from html import unescape
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract

BASE="https://t.me/s/BlueWhaleCryptoTrading"
BINANCE="https://data-api.binance.vision/api/v3/klines"
UA="Mozilla/5.0 (compatible; BlueWhaleEvidencePack/1.0)"
MAX_PAGES=20
WINDOW_HOURS=72
MAX_IMAGES_PER_POST=2

def fetch_text(url):
    req=urllib.request.Request(url,headers={"User-Agent":UA})
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.read().decode("utf-8",errors="replace")

def fetch_bytes(url):
    req=urllib.request.Request(url,headers={"User-Agent":UA})
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.read()

def clean_html(s):
    s=re.sub(r"<br\s*/?>","\n",s,flags=re.I)
    s=re.sub(r"<[^>]+>"," ",s)
    s=unescape(s)
    s=re.sub(r"[ \t\r\f\v]+"," ",s)
    s=re.sub(r"\n\s+","\n",s)
    return s.strip()

def collect_posts():
    seen={}; before=None
    for _ in range(MAX_PAGES):
        url=BASE if before is None else BASE+"?"+urllib.parse.urlencode({"before":before})
        html=fetch_text(url)
        chunks=re.split(r'(?=<div class="tgme_widget_message_wrap)',html)
        posts=[]
        for ch in chunks:
            m=re.search(r'data-post="BlueWhaleCryptoTrading/(\d+)"',ch)
            if not m: continue
            mid=int(m.group(1))
            dtm=re.search(r'<time[^>]+datetime="([^"]+)"',ch)
            tm=re.search(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>',ch,flags=re.S)
            txt=clean_html(tm.group(1)) if tm else ""
            imgs=re.findall(r"background-image:url\('([^']+)'\)",ch)
            imgs=[u for u in imgs if "telesco.pe/file/" in u]
            posts.append({"id":mid,"dt":dtm.group(1) if dtm else None,"text":txt,"images":list(dict.fromkeys(imgs))})
        if not posts: break
        for p in posts: seen[p["id"]]=p
        oldest=min(p["id"] for p in posts)
        if before is not None and oldest>=before: break
        before=oldest
        time.sleep(0.12)
    return [seen[k] for k in sorted(seen)]

def dtparse(s): return datetime.fromisoformat(s.replace("Z","+00:00"))
def ms(x): return int(x.timestamp()*1000)

def parse_stop(text):
    u=text.upper().replace("$","")
    m=re.search(r'\bSL\s*[:=]?\s*([0-9]{2,3}(?:,[0-9]{1,3})?(?:X{1,3})?)',u)
    if not m: return None
    shown=m.group(1)
    raw=shown.replace(",","")
    if "X" not in raw:
        try:
            v=float(raw)
            # Guard against malformed truncation; BTC stops in this sample are 5 digits.
            if v<10000: return None
            return {"raw":shown,"low":v,"high":v}
        except: return None
    n=raw.count("X"); prefix=raw[:-n]
    if not prefix.isdigit(): return None
    low=float(int(prefix)*(10**n))
    return {"raw":shown,"low":low,"high":low+(10**n)-1}

def market_rows(start,end):
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
        cur=nxt; time.sleep(0.02)
    return out

def market_price_at(rows,t):
    row=min(rows,key=lambda x:abs(int(x[0])-ms(t)))
    return float(row[4])

def prep(img):
    if img.mode!="RGB": img=img.convert("RGB")
    if max(img.size)<1800:
        img=img.resize((img.width*2,img.height*2))
    gray=img.convert("L")
    gray=ImageEnhance.Contrast(gray).enhance(1.8)
    return gray.filter(ImageFilter.SHARPEN)

def inspect_images(urls):
    items=[]
    for u in urls:
        try:
            data=fetch_bytes(u)
            img=Image.open(io.BytesIO(data))
            items.append({"url":u,"data":data,"size":[img.width,img.height],"area":img.width*img.height})
        except Exception:
            pass
    items.sort(key=lambda x:x["area"],reverse=True)
    return items[:MAX_IMAGES_PER_POST]

def ocr_post(post):
    texts=[]
    meta=[]
    for item in inspect_images(post.get("images",[])):
        try:
            img=Image.open(io.BytesIO(item["data"]))
            txt=pytesseract.image_to_string(prep(img),lang="eng",config="--psm 6").strip()
            texts.append(txt)
            meta.append({"url":item["url"],"size":item["size"],"ocr":txt[:4000]})
        except Exception as e:
            meta.append({"url":item["url"],"size":item["size"],"error":repr(e)})
    return "\n\n".join(texts),meta

def norm_num(s):
    s=s.strip().replace("$","").replace(" ","")
    # If both comma and dot occur, comma is thousands separator.
    if "," in s and "." in s:
        s=s.replace(",","")
    elif "," in s:
        # 75,681.8 handled above; 77.280,0 OCR locale -> thousands dot, decimal comma
        if re.match(r'^\d{1,3}(,\d{3})+$',s):
            s=s.replace(",","")
        else:
            s=s.replace(",",".")
    # OCR locale like 77.280,0 may arrive with both and handled poorly above.
    if s.count(".")>1:
        parts=s.split(".")
        s="".join(parts[:-1])+"."+parts[-1]
    try:
        v=float(s)
        if 10000<=v<=200000: return v
    except: pass
    return None

def labelled_prices(text):
    out={"entry":[],"close":[],"mark":[]}
    patterns={
      "entry":[
        r'Avg\.?\s*entry\s*price\s*[:=]?\s*([0-9][0-9,\. ]{3,12})',
        r'Entry\s*Price(?:\s*\(USDT\))?\s*[:=]?\s*([0-9][0-9,\. ]{3,12})',
        r'Entry\s*[:=]\s*([0-9][0-9,\. ]{3,12})',
      ],
      "close":[
        r'Close\s*price\s*[:=]?\s*([0-9][0-9,\. ]{3,12})',
        r'Filled\s*Price\s*[:=]?\s*([0-9][0-9,\. ]{3,12})',
      ],
      "mark":[r'Mark\s*Price(?:\s*\(USDT\))?\s*[:=]?\s*([0-9][0-9,\. ]{3,12})']
    }
    for k,ps in patterns.items():
        for p in ps:
            for m in re.finditer(p,text,flags=re.I):
                v=norm_num(m.group(1))
                if v is not None: out[k].append(v)
    for k in out:
        # stable unique
        seen=[]; arr=[]
        for v in out[k]:
            if round(v,4) not in seen:
                seen.append(round(v,4)); arr.append(v)
        out[k]=arr
    return out

def explicit_side(text):
    u=text.upper()
    long=bool(re.search(r'\bLONG\b',u))
    short=bool(re.search(r'\bSHORT\b',u))
    if long and not short:return "LONG"
    if short and not long:return "SHORT"
    return None

def infer_side(caption,ocr,stop,entry):
    s=explicit_side(caption+"\n"+ocr)
    if s:return s
    if entry is not None and stop:
        if stop["high"]<entry*0.995:return "LONG"
        if stop["low"]>entry*1.005:return "SHORT"
    return "UNKNOWN"

def outcome_metrics(rows,start,end,side,entry,stop):
    sub=[x for x in rows if ms(start)<=int(x[0])<=ms(end)]
    if not sub or entry is None or side not in ("LONG","SHORT"): return {}
    hi=max(float(x[2]) for x in sub); lo=min(float(x[3]) for x in sub)
    if side=="LONG":
        mfe=(hi/entry-1)*100; mae=(lo/entry-1)*100
        if stop:
            st="DEFINITELY_HIT" if lo<=stop["low"] else ("DEFINITELY_NOT_HIT" if lo>stop["high"] else "AMBIGUOUS")
        else: st=None
    else:
        mfe=(entry/lo-1)*100; mae=(entry/hi-1)*100
        if stop:
            st="DEFINITELY_HIT" if hi>=stop["high"] else ("DEFINITELY_NOT_HIT" if hi<stop["low"] else "AMBIGUOUS")
        else: st=None
    return {"window_high":hi,"window_low":lo,"mfe_pct":mfe,"mae_pct":mae,"stop_status":st}

def resultish(text):
    u=text.upper()
    return any(k in u for k in ["PROFIT","HIT TP","RESULT","HOLD","BIG","CLOSE","TP"])

def main():
    posts=collect_posts()
    sigs=[]
    for p in posts:
        if not p["dt"] or "BTC" not in p["text"].upper():continue
        st=parse_stop(p["text"])
        if st:sigs.append({**p,"stop":st})

    # cluster repeated same stop within 72h
    clusters=[]
    for s in sigs:
        t=dtparse(s["dt"]); matched=None
        for c in reversed(clusters):
            if c["stop"]["low"]==s["stop"]["low"] and c["stop"]["high"]==s["stop"]["high"] and t-dtparse(c["first"]["dt"])<=timedelta(hours=72):
                matched=c;break
        if matched: matched["reposts"].append(s)
        else: clusters.append({"first":s,"stop":s["stop"],"reposts":[]})

    evidence=[]
    for c in clusters:
        first=c["first"]; start=dtparse(first["dt"]); end=start+timedelta(hours=WINDOW_HOURS)
        sig_ocr,sig_imgs=ocr_post(first)
        prices=labelled_prices(sig_ocr)
        exact_entry=prices["entry"][0] if prices["entry"] else None

        rows=market_rows(start-timedelta(minutes=2),end+timedelta(minutes=2))
        proxy=market_price_at(rows,start) if rows else None
        freshness=None if exact_entry is None or proxy is None else abs(exact_entry/proxy-1)*100
        side=infer_side(first["text"],sig_ocr,c["stop"],exact_entry or proxy)

        follow=[]
        exact_closes=[]
        for p in posts:
            if not p["dt"] or p["id"]<=first["id"] or "BTC" not in p["text"].upper():continue
            tp=dtparse(p["dt"])
            if not(start<tp<=end):continue
            if not resultish(p["text"]):continue
            ocr,imgs=ocr_post(p)
            lp=labelled_prices(ocr)
            if lp["close"]:
                exact_closes.extend([{"post_id":p["id"],"dt":p["dt"],"price":v} for v in lp["close"]])
            # keep only posts with useful OCR labels or obvious updates
            if lp["entry"] or lp["close"] or lp["mark"] or "HOLD" in p["text"].upper() or "PROFIT" in p["text"].upper() or "HIT TP" in p["text"].upper():
                follow.append({"id":p["id"],"dt":p["dt"],"caption":p["text"][:300],"prices":lp,"ocr_images":imgs})

        exact_close=exact_closes[0]["price"] if exact_closes else None
        exact_raw_return=None
        if exact_entry is not None and exact_close is not None and side in ("LONG","SHORT"):
            exact_raw_return=((exact_close/exact_entry-1)*100) if side=="LONG" else ((exact_entry/exact_close-1)*100)

        ev={
            "signal_id":first["id"],"signal_dt":first["dt"],"caption":first["text"],
            "stop":c["stop"],"repost_count":len(c["reposts"]),
            "exact_entry":exact_entry,"entry_candidates":prices["entry"],
            "market_proxy_at_post":proxy,"entry_freshness_abs_pct":freshness,
            "side":side,"exact_close":exact_close,"exact_close_candidates":exact_closes,
            "exact_raw_return_pct":exact_raw_return,
            "signal_ocr_images":sig_imgs,
            "followups":follow[:12],
        }
        ev.update(outcome_metrics(rows,start,end,side,exact_entry or proxy,c["stop"]))
        evidence.append(ev)
        print(f"cluster {first['id']} entry={exact_entry} side={side} close={exact_close}",flush=True)

    exact_entries=[e for e in evidence if e["exact_entry"] is not None]
    exact_closed=[e for e in evidence if e["exact_raw_return_pct"] is not None]
    fresh05=[e for e in exact_entries if e["entry_freshness_abs_pct"] is not None and e["entry_freshness_abs_pct"]<=0.5]
    fresh10=[e for e in exact_entries if e["entry_freshness_abs_pct"] is not None and e["entry_freshness_abs_pct"]<=1.0]
    summary={
        "clusters":len(evidence),
        "exact_entry_clusters":len(exact_entries),
        "exact_closed_clusters":len(exact_closed),
        "entry_within_0_5pct_of_public_post":len(fresh05),
        "entry_within_1pct_of_public_post":len(fresh10),
        "exact_closed_positive":sum((e["exact_raw_return_pct"] or 0)>0 for e in exact_closed),
        "exact_closed_returns_pct":[e["exact_raw_return_pct"] for e in exact_closed],
    }
    result={"summary":summary,"evidence":evidence,"warning":"OCR-derived values require visual cross-check. Exact close is counted only when a public follow-up image exposes Close/Filled price."}
    open("blue_whale_evidence_pack.json","w",encoding="utf-8").write(json.dumps(result,ensure_ascii=False,indent=2))
    print("RESULT_JSON="+json.dumps(result,ensure_ascii=False,sort_keys=True),flush=True)

if __name__=="__main__":
    main()
