#!/usr/bin/env python3
"""
OCR a LIMITED set of recent public BlueWhaleCryptoTrading BTC post images.

Purpose: recover entry/exit/TP information that may be visible in the public
screenshots even when the Telegram caption withholds it.

Scope:
- public Telegram preview only
- BTC posts since 2026-08-01
- first non-emoji telesco.pe image per post
- only signal/update/result-like posts
- hard cap 30 images
"""
from __future__ import annotations
import io, json, re, time, urllib.request, urllib.parse
from datetime import datetime, timezone
from html import unescape
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract

BASE="https://t.me/s/BlueWhaleCryptoTrading"
UA="Mozilla/5.0 (compatible; BlueWhaleImageOCR/1.0)"
MAX_PAGES=20
MAX_IMAGES=30

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

def collect():
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
        time.sleep(0.15)
    return [seen[k] for k in sorted(seen)]

def interesting(text):
    u=text.upper()
    if "BTC" not in u: return False
    return any(k in u for k in ["SL", "LONG", "SHORT", "ENTRY", "OPEN", "HOLD", "PROFIT", "HIT TP", "RESULT", "BIG"])

def prep(img):
    # Upscale and create two OCR-friendly variants.
    if img.mode!="RGB": img=img.convert("RGB")
    scale=2 if max(img.size)<1800 else 1
    if scale>1: img=img.resize((img.width*scale,img.height*scale))
    gray=img.convert("L")
    gray=ImageEnhance.Contrast(gray).enhance(1.8)
    gray=gray.filter(ImageFilter.SHARPEN)
    return gray

def ocr_image(data):
    img=Image.open(io.BytesIO(data))
    proc=prep(img)
    text=pytesseract.image_to_string(proc,lang="eng",config="--psm 6")
    return {"size":[img.width,img.height],"text":text.strip()}

def extract_numbers(text):
    # price/account-looking tokens
    vals=re.findall(r'(?<!\w)[+-]?\$?\d{1,3}(?:[,. ]\d{3})+(?:\.\d+)?|(?<!\w)\d{4,6}(?:\.\d+)?',text)
    return list(dict.fromkeys(v.strip() for v in vals))[:30]

def main():
    posts=collect()
    cutoff=datetime(2026,8,1,tzinfo=timezone.utc)
    candidates=[]
    for p in posts:
        if not p["dt"] or not p["images"] or not interesting(p["text"]): continue
        d=datetime.fromisoformat(p["dt"].replace("Z","+00:00"))
        if d<cutoff: continue
        candidates.append(p)
    # newest first, limit.
    candidates=sorted(candidates,key=lambda x:x["id"],reverse=True)[:MAX_IMAGES]
    results=[]
    for p in candidates:
        url=p["images"][0]
        try:
            data=fetch_bytes(url)
            o=ocr_image(data)
            results.append({
                "id":p["id"],"dt":p["dt"],"caption":p["text"][:500],
                "image_url":url,"image_size":o["size"],
                "ocr_text":o["text"][:4000],
                "numbers":extract_numbers(o["text"]),
            })
            print(f"OCR id={p['id']} chars={len(o['text'])}",flush=True)
        except Exception as e:
            results.append({"id":p["id"],"dt":p["dt"],"caption":p["text"][:500],"image_url":url,"error":repr(e)})
    print("RESULT_JSON="+json.dumps({
        "posts_ocrd":len(results),
        "cutoff":"2026-08-01T00:00:00Z",
        "results":results,
        "warning":"OCR is machine extraction from public screenshots and must be cross-checked before treating values as exact."
    },ensure_ascii=False,sort_keys=True),flush=True)

if __name__=="__main__":
    main()
