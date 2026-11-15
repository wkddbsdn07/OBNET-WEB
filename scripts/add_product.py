#!/usr/bin/env python3
"""Add an OBNOTE product to products.json with a unique sequential code.

Run from the repository root, for example:
    python scripts/add_product.py --name "Cable Organizer" --category "DESK TECH" --description "A desk accessory."
Or use --from-env inside a GitHub Actions workflow.
Only the workflow/CLI writes the catalog: GitHub Pages never stores secrets.
"""
import argparse
import json
import os
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "products.json"
FIRST_CODE = 1001


def fail(message):
    raise ValueError(message)


def text(value, label, required=False, limit=1000):
    value = (value or "").strip()
    if required and not value:
        fail(f"{label} is required")
    if len(value) > limit:
        fail(f"{label} must be {limit} characters or less")
    return value


def https_url(value, label):
    value = text(value, label, limit=2048)
    if not value:
        return None
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        fail(f"{label} must be an HTTPS URL with no embedded credentials")
    return value


def parse_price(value):
    value = (value or "").strip()
    if not value:
        return None
    try:
        price = Decimal(value)
    except InvalidOperation:
        fail("Price must be a positive number, or blank")
    if not price.is_finite() or price <= 0 or price > 100000000:
        fail("Price must be a positive finite number under 100,000,000")
    if price.as_tuple().exponent < -2:
        fail("Price may have at most two decimal places")
    return float(price)


def next_code(products):
    codes = [p.get("code") for p in products]
    if len(codes) != len({str(c) for c in codes}):
        fail("Duplicate codes already exist in products.json; refusing to write")
    numeric = [int(str(code)) for code in codes if re.fullmatch(r"[0-9]+", str(code))]
    number = max([FIRST_CODE - 1] + numeric) + 1
    candidate = str(number).zfill(4)
    if candidate in {str(c) for c in codes}:
        fail(f"Code collision: {candidate}")
    return candidate


def add_product(values, catalog=CATALOG):
    products = json.loads(catalog.read_text(encoding="utf-8"))
    if not isinstance(products, list):
        fail("products.json must contain an array")
    if any(not isinstance(p, dict) or "code" not in p for p in products):
        fail("All existing products must be objects with codes")

    name = text(values.get("name"), "Name", required=True, limit=110)
    category = text(values.get("category"), "Category", required=True, limit=40)
    description = text(values.get("description"), "Description", required=True, limit=1300)
    tagline = text(values.get("tagline"), "Tagline", limit=220)
    currency = text(values.get("currency") or "USD", "Currency", limit=3).upper()
    if not re.fullmatch(r"[A-Z]{3}", currency):
        fail("Currency must be a three-letter code such as USD or KRW")
    raw_features = values.get("features") or ""
    features = [text(x, "Feature", limit=180) for x in raw_features.split("|") if x.strip()]
    if len(features) > 8:
        fail("Use at most eight features, separated by |")
    demo = str(values.get("is_demo", "true")).lower() in ("true", "1", "yes")
    image_url = https_url(values.get("image_url"), "Image URL")
    purchase_url = https_url(values.get("purchase_url"), "Purchase URL")
    price = parse_price(values.get("price"))

    if demo:
        # Demo listings must never link to a checkout or imply verified pricing.
        purchase_url = None
        price = None
    if not demo and purchase_url is None:
        # Real product listings without approved seller links are allowed.
        pass

    product = {
        "code": next_code(products),
        "name": name,
        "category": category,
        "tagline": tagline,
        "description": description,
        "features": features,
        "image_url": image_url,
        "price": price,
        "currency": currency,
        "purchase_url": purchase_url,
        "is_demo": demo,
    }
    products.append(product)
    # Only write once all validations and duplicate checks have succeeded.
    catalog.write_text(json.dumps(products, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return product["code"]


def main():
    parser = argparse.ArgumentParser(description="Register OBNOTE product and auto-issue a code")
    parser.add_argument("--from-env", action="store_true", help="Read PRODUCT_* values set by GitHub Actions")
    for key in ("name", "category", "tagline", "description", "features", "image_url", "price", "currency", "purchase_url", "is_demo"):
        parser.add_argument("--" + key.replace("_", "-"))
    args = parser.parse_args()
    keys = ("name", "category", "tagline", "description", "features", "image_url", "price", "currency", "purchase_url", "is_demo")
    if args.from_env:
        values = {key: os.environ.get("PRODUCT_" + key.upper(), "") for key in keys}
    else:
        values = {key: getattr(args, key) for key in keys}
    try:
        code = add_product(values)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"Registration failed: {exc}", file=sys.stderr)
        return 1
    print(f"Registered product code: {code}")
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(f"code={code}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
