#!/usr/bin/env python3
"""Create original, fact-limited English Shorts narration and SRT subtitles.

This is deterministic templating, NOT AI-generated copy.
Only uses facts already in the published OBNOTE catalog.
No external audio, artwork, or third-party text is added.
"""
import argparse
import json
import os
from pathlib import Path
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DB = "https://bidcctugofnvfilywick.supabase.co"
DURATIONS = [2.4, 2.2, 2.8, 2.0, 3.0]


def fetch_product(code, key):
    if not re.fullmatch(r"[A-Za-z0-9-]{1,24}", code):
        raise ValueError("Invalid product code")
    if not key.startswith("sb_publishable_"):
        raise ValueError("Missing publishable API key")
    q = urlencode({
        "select": "code,name,tagline,description,features,is_demo,purchase_url",
        "code": "eq." + code, "published": "eq.true"
    })
    with urlopen(Request(DB+"/rest/v1/products?"+q,
                        headers={"apikey":key,"Accept":"application/json"}),
                 timeout=25) as response:
        result = json.load(response)
    if not isinstance(result, list) or len(result) != 1:
        raise ValueError("No published product matches " + code)
    return result[0]


def plain(value, limit=170):
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def storyboard(product):
    name = plain(product["name"], 100)
    code = plain(product["code"], 24)
    is_demo = bool(product.get("is_demo"))
    tag = plain(product.get("tagline"), 54)
    features = [plain(x, 55) for x in product.get("features", []) if plain(x)][:1]
    third = ("Concept preview. Not a real product."
             if is_demo else
             (". ".join(features)+("." if features else "")
              if features else "View the product details using its code."))
    captions = [
        "Meet " + name + ".",
        tag + ("." if tag and tag[-1] not in ".!?" else "") if tag else "A fresh desk tech discovery.",
        third,
        "See it. Search it. Explore it.",
        "Search OBNOTE for product code " + code + "."
    ]
    script = []
    moment = 0.0
    for duration, words in zip(DURATIONS, captions):
        script.append({
            "start_seconds": round(moment, 2),
            "end_seconds": round(moment + duration, 2),
            "narration": words,
            "caption": words,
        })
        moment += duration
    return {"code": code, "product": name, "is_demo": is_demo,
            "mode": "template_without_ai", "segments": script,
            "disclosure": "Concept demo; not a real product" if is_demo
              else "Check the seller for current details. Affiliate disclosures may apply."}


def srt_time(seconds):
    total = int(round(seconds * 1000))
    h, rem = divmod(total, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def srt_text(plan):
    chunks = []
    for idx, item in enumerate(plan["segments"], 1):
        chunks.append(
            str(idx)+"\n"+srt_time(item["start_seconds"])+" --> "
            +srt_time(item["end_seconds"])+"\n"+item["caption"]+"\n"
        )
    return "\n".join(chunks)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", default="1001")
    parser.add_argument("--outdir", default="dist")
    args = parser.parse_args()
    product = fetch_product(args.code, os.getenv("OBNOTE_SUPABASE_PUBLIC_KEY",""))
    plan = storyboard(product)
    folder = Path(args.outdir)
    folder.mkdir(parents=True, exist_ok=True)
    base = folder / ("obnote-" + args.code)
    (Path(str(base) + "-script.json")).write_text(json.dumps(plan,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    (Path(str(base) + "-captions.srt")).write_text(srt_text(plan),encoding="utf-8")
    print("Created original narration JSON and caption SRT for product",args.code)


if __name__ == "__main__":
    main()
