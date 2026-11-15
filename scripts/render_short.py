#!/usr/bin/env python3
"""Render an original 1080x1920 OBNOTE Shorts template from a published product.

No scraped images, music, AI generated claims or paid services.
No upload to YouTube. Artwork is typography + original geometric shapes.
Use inside GitHub Actions; downloaded MP4 is an Actions artifact.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import urlencode
from urllib.request import Request
from catalog_http import fetch_json

from PIL import Image, ImageDraw, ImageFont
from imageio_ffmpeg import get_ffmpeg_exe

WIDTH, HEIGHT = 1080, 1920
DB = "https://bidcctugofnvfilywick.supabase.co"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
INK = (233, 240, 249)
MUTED = (159, 177, 196)
SILVER = (200, 214, 229)
FAINT = (49, 62, 79)


def font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT, size)


def get_product(code, key):
    if not re.fullmatch(r"[A-Za-z0-9-]{1,24}", code):
        raise ValueError("Invalid product code")
    if not key.startswith("sb_publishable_"):
        raise ValueError("A public Supabase key is required")
    query = urlencode({"select": "code,name,category,tagline,description,features,is_demo", "code": "eq." + code, "published": "eq.true"})
    url = DB + "/rest/v1/products?" + query
    result = fetch_json(Request(url, headers={"apikey": key, "Accept": "application/json"}), timeout=30)
    if not isinstance(result, list) or len(result) != 1:
        raise ValueError("Published product not found: " + code)
    return result[0]


def fit_lines(draw, value, size, max_width, max_lines=3):
    value = re.sub(r"\s+", " ", str(value or "")).strip()
    if not value:
        return []
    output = []
    current = ""
    for word in value.split():
        candidate = (current + " " + word).strip()
        if draw.textbbox((0, 0), candidate, font=font(size, True))[2] <= max_width:
            current = candidate
        else:
            if current:
                output.append(current)
            current = word
        if len(output) >= max_lines:
            break
    if current and len(output) < max_lines:
        output.append(current)
    if len(output) == max_lines:
        original = value
        rendered = " ".join(output)
        if len(rendered) < len(original):
            last = output[-1]
            while last and draw.textbbox((0, 0), last + "...", font=font(size, True))[2] > max_width:
                last = last[:-1]
            output[-1] = last.rstrip() + "..."
    return output


def background():
    image = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        t = y / HEIGHT
        draw.line((0, y, WIDTH, y), fill=(
            int(9 + 7 * t), int(12 + 9 * t), int(20 + 12 * t)
        ))
    draw.polygon([(790, -160), (1070, -160), (470, 1360), (315, 1360)],
                 fill=(24, 34, 47))
    draw.polygon([(1025, -180), (1065, -180), (460, 1400), (419, 1400)],
                 fill=(73, 88, 106))
    draw.line([(50, 245), (1030, 245)], fill=FAINT, width=2)
    draw.line([(50, 1600), (1030, 1600)], fill=FAINT, width=2)
    return image


def emblem(draw, x, y, radius=28):
    points = []
    import math
    for n in range(8):
        angle = math.pi / 8 + n * math.pi / 4
        points.append((x + int(radius * math.cos(angle)),
                       y + int(radius * math.sin(angle))))
    draw.line(points + [points[0]], fill=SILVER, width=5, joint="curve")


def layout(draw, product, scene):
    emblem(draw, 80, 112)
    draw.text((124, 78), "OBNOTE", font=font(38, True), fill=INK)
    draw.text((54, 170), "CURATED TECH  /  WORKSPACE DISCOVERIES",
              font=font(22, True), fill=MUTED)
    draw.text((55, 1635), "DISCOVER WHAT'S NEXT", font=font(30, True), fill=MUTED)
    draw.text((55, 1730), "OBNOTE  |  PRODUCT #" + product["code"],
              font=font(25), fill=SILVER)
    if product.get("is_demo"):
        draw.text((55, 1805), "CONCEPT DEMO  |  NOT A REAL PRODUCT",
                  font=font(19, True), fill=MUTED)
    else:
        draw.text((55, 1805), "CHECK SELLER FOR CURRENT DETAILS",
                  font=font(19, True), fill=MUTED)
    draw.text((940, 1745), f"{scene + 1}/5", font=font(25, True), fill=MUTED)


def centered_lines(draw, lines, size, top, color=INK, gap=22):
    fnt = font(size, True)
    y = top
    for line in lines:
        bounds = draw.textbbox((0, 0), line, font=fnt)
        width = bounds[2] - bounds[0]
        draw.text(((WIDTH - width) / 2, y), line, font=fnt, fill=color)
        y += size + gap


def render_caption(draw, label):
    """Draw source-backed captions directly, avoiding external subtitle codecs."""
    if not label:
        return
    label = re.sub(r"\s+", " ", str(label)).strip()[:200]
    # Captions stay inside the Shorts center safe zone, above footer metadata.
    lines = fit_lines(draw, label, 38, 840, 2)
    if not lines:
        return
    top = 1450 - (len(lines) - 1) * 25
    draw.rounded_rectangle((65, top - 23, 1015, top + 55 * len(lines) + 28),
                           radius=20, fill=(13, 19, 29))
    centered_lines(draw, lines, 38, top, INK, 13)


def draw_scene(product, i, caption=None):
    image = background()
    draw = ImageDraw.Draw(image)
    layout(draw, product, i)
    if i == 0:
        centered_lines(draw, ["MEET YOUR", "NEXT IDEA."], 105, 680)
        centered_lines(draw, fit_lines(draw, product["name"], 47, 800, 2),
                       47, 1060, SILVER)
    elif i == 1:
        centered_lines(draw, ["SMALL DETAILS.", "SMARTER DESKS."], 72, 650)
        tagline = product.get("tagline") or "Discover a fresh perspective on desk tech."
        centered_lines(draw, fit_lines(draw, tagline, 40, 850, 3),
                       40, 1010, SILVER, 16)
    elif i == 2:
        centered_lines(draw, ["THE DETAILS."], 88, 540)
        features = [str(x) for x in (product.get("features") or [])][:3]
        if product.get("is_demo"):
            features = ["Fictional concept", "Made for design preview", "No real purchase link"]
        if not features:
            features = [str(product.get("category", "TECH")), "See product details by code"]
        y = 790
        for feat in features:
            for line in fit_lines(draw, feat, 43, 820, 2):
                draw.text((126, y), "  " + line, font=font(43, True), fill=SILVER)
                y += 78
            y += 26
    elif i == 3:
        centered_lines(draw, ["SEE IT.", "SEARCH IT.", "EXPLORE IT."], 76, 660)
        centered_lines(draw, ["ONE CODE. ONE PRODUCT."], 34, 1120, SILVER)
    else:
        centered_lines(draw, ["FIND IT BY CODE"], 63, 615, SILVER)
        centered_lines(draw, [str(product["code"])], 180, 815, INK)
        centered_lines(draw, ["SEARCH ON OBNOTE"], 52, 1150, SILVER)
        centered_lines(draw, ["obnote.vercel.app"], 44, 1290, SILVER)
    render_caption(draw, caption)
    return image


def render(product, output, plan=None):
    code = str(product["code"])
    folder = output.parent / ("frames-" + code)
    folder.mkdir(parents=True, exist_ok=True)
    frames = []
    for i in range(5):
        path = folder / f"scene-{i + 1}.png"
        caption = plan["segments"][i]["caption"] if plan else None
        draw_scene(product, i, caption).save(path)
        frames.append(path)
    sequence = folder / "frames.txt"
    durations = [2.4, 2.2, 2.8, 2.0, 3.0]
    lines = ["file '" + p.name + "'\nduration " + str(t) + "\n"
             for p, t in zip(frames, durations)]
    lines.append("file '" + frames[-1].name + "'\n")
    sequence.write_text("".join(lines), encoding="utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
        "-f", "concat", "-safe", "0", "-i", str(sequence),
        "-vf", "fps=24,format=yuv420p",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
        "-movflags", "+faststart", str(output)
    ], check=True)
    print("Rendered original silent 1080x1920 Shorts template:", output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", default="1001")
    parser.add_argument("--out", default="")
    parser.add_argument("--storyboard", default="", help="Narration storyboard JSON for captions")
    args = parser.parse_args()
    key = os.environ.get("OBNOTE_SUPABASE_PUBLIC_KEY", "")
    product = get_product(args.code, key)
    output = Path(args.out or ("dist/obnote-" + args.code + "-short.mp4"))
    plan = None
    if args.storyboard:
        plan = json.loads(Path(args.storyboard).read_text(encoding="utf-8"))
        if str(plan.get("code")) != str(product["code"]) or len(plan.get("segments", [])) != 5:
            raise ValueError("Storyboard must describe this product and exactly five scenes")
    render(product, output, plan)


if __name__ == "__main__":
    main()
