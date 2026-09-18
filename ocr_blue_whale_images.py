#!/usr/bin/env python3
"""
OCR recent public BlueWhaleCryptoTrading BTC post images.

Improved version:
- examines ALL public telesco.pe images attached to each post;
- chooses up to the 2 largest images by pixel area instead of blindly taking
  the first thumbnail;
- OCRs only BTC signal/update/result-like posts since 2026-08-01;
- keeps a hard cap on posts to stay deterministic and cheap.
"""
from __future__ import annotations
import io, json, re, time, urllib.request, urllib.parse
from datetime import datetime, timezone
from html import unescape
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract

BASE="https://t.me/s/BlueWhaleCryptoTrading"
UA="Mozilla/5.0 (compatible; BlueWhaleImageOCR/2.0)"
MAX_PAGES=20
MAX_POSTS=30
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
    return any(k in u for k in ["SL","LONG","SHORT","ENTRY","OPEN","HOLD","PROFIT","HIT TP","RESULT","BIG"])

def prep(img):
    if img.mode!="RGB": img=img.convert("RGB")
    scale=2 if max(img.size)<1800 else 1
    if scale>1: img=img.resize((img.width*scale,img.height*scale))
    gray=img.convert("L")
    gray=ImageEnhance.Contrast(gray).enhance(1.8)
    return gray.filter(ImageFilter.SHARPEN)

def inspect_image(url):
    data=fetch_bytes(url)
    img=Image.open(io.BytesIO(data))
    return {"url":url,"data":data,"size":[img.width,img.height],"area":img.width*img.height}

def ocr_image(item):
    img=Image.open(io.BytesIO(item["data"]))
    text=pytesseract.image_to_string(prep(img),lang="eng",config="--psm 6").strip()
    return {
        "image_url":item["url"],
        "image_size":item["size"],
        "ocr_text":text[:5000],
        "numbers":extract_numbers(text),
    }

def extract_numbers(text):
    vals=re.findall(r'(?<!\w)[+-]?\$?\d{1,3}(?:[,. ]\d{3})+(?:\.\d+)?|(?<!\w)\d{4,6}(?:\.\d+)?',text)
    return list(dict.fromkeys(v.strip() for v in vals))[:40]

def main():
    posts=collect()
    cutoff=datetime(2026,8,1,tzinfo=timezone.utc)
    candidates=[]
    for p in posts:
        if not p["dt"] or not p["images"] or not interesting(p["text"]): continue
        d=datetime.fromisoformat(p["dt"].replace("Z","+00:00"))
        if d>=cutoff: candidates.append(p)
    candidates=sorted(candidates,key=lambda x:x["id"],reverse=True)[:MAX_POSTS]

    results=[]
    for p in candidates:
        inspected=[]
        for url in p["images"]:
            try:
                inspected.append(inspect_image(url))
            except Exception:
                pass
        inspected.sort(key=lambda x:x["area"],reverse=True)
        chosen=inspected[:MAX_IMAGES_PER_POST]
        images=[]
        for item in chosen:
            try:
                images.append(ocr_image(item))
            except Exception as e:
                images.append({"image_url":item["url"],"image_size":item["size"],"error":repr(e)})
        results.append({
            "id":p["id"],"dt":p["dt"],"caption":p["text"][:700],
            "public_image_count":len(p["images"]),
            "ocr_images":images,
        })
        print(f"OCR id={p['id']} images={len(images)}",flush=True)

    print("RESULT_JSON="+json.dumps({
        "posts_ocrd":len(results),
        "cutoff":"2026-08-01T00:00:00Z",
        "selection":"up to 2 largest public images per post",
        "results":results,
        "warning":"OCR is machine extraction from public screenshots and must be cross-checked before treating values as exact."
    },ensure_ascii=False,sort_keys=True),flush=True)

if __name__=="__main__":
    main()
