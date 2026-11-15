#!/usr/bin/env python3
"""OBNOTE secure product management via Supabase.

Intended to run server-side (GitHub Actions or Hermes), never in a browser.
Requires OBNOTE_SUPABASE_SECRET_KEY in its environment. This key must remain secret.

Usage:
    python3 scripts/manage_products.py add
    python3 scripts/manage_products.py edit
    python3 scripts/manage_products.py delete

Inputs are supplied through PRODUCT_* environment variables by GitHub Actions.
"""
import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SUPABASE_URL = "https://bidcctugofnvfilywick.supabase.co"
RPC_URL = SUPABASE_URL + "/rest/v1/rpc/obnote_manage_product"

EDITABLE = {
    "name", "category", "tagline", "description", "features",
    "image_url", "price", "currency", "purchase_url", "is_demo", "published",
    "stock_status"
}


def parse_boolean(value):
    lowered = (value or "").strip().lower()
    if lowered in ("true", "1", "yes", "on"):
        return True
    if lowered in ("false", "0", "no", "off"):
        return False
    raise ValueError("Boolean fields accept true or false")


def stock_status(value):
    result = (value or "unknown").strip().lower()
    if result not in ("unknown", "in_stock", "out_of_stock", "preorder"):
        raise ValueError("Stock must be unknown, in_stock, out_of_stock, or preorder")
    return result


def product_payload():
    required = ("PRODUCT_NAME", "PRODUCT_DESCRIPTION")
    for name in required:
        if not os.getenv(name, "").strip():
            raise ValueError(name + " is required")

    def val(name):
        return os.getenv("PRODUCT_" + name, "").strip()

    is_demo = parse_boolean(os.getenv("PRODUCT_IS_DEMO", "true"))
    image_url = val("IMAGE_URL") or None
    purchase_url = val("PURCHASE_URL") or None
    if image_url and not image_url.startswith("https://"):
        raise ValueError("Only HTTPS image URLs are allowed")
    if purchase_url and not purchase_url.startswith("https://"):
        raise ValueError("Only HTTPS purchase URLs are allowed")
    price = val("PRICE") or None
    availability = stock_status(val("STOCK_STATUS"))

    # Demo entries never advertise a checkout or a verified price.
    if is_demo:
        purchase_url = None
        price = None
        availability = "unknown"

    return {
        "name": val("NAME"),
        "category": val("CATEGORY") or "TECH",
        "tagline": val("TAGLINE"),
        "description": val("DESCRIPTION"),
        "features": [item.strip() for item in val("FEATURES").split("|") if item.strip()][:8],
        "image_url": image_url,
        "price": price,
        "currency": (val("CURRENCY") or "USD").upper(),
        "purchase_url": purchase_url,
        "is_demo": is_demo,
        "published": True,
        "stock_status": availability,
    }


def edit_payload(field, value):
    if field not in EDITABLE:
        raise ValueError("Unsupported edit field")
    if field == "stock_status":
        return {field: stock_status(value)}
    if field == "features":
        return {field: [item.strip() for item in value.split("|") if item.strip()][:8]}
    if field in ("price", "image_url", "purchase_url"):
        if value and field.endswith("_url") and not value.startswith("https://"):
            raise ValueError("Only HTTPS URLs are allowed")
        return {field: value or None}
    if field in ("is_demo", "published"):
        return {field: parse_boolean(value)}
    if field in ("name", "category") and not value:
        raise ValueError(field + " cannot be empty")
    return {field: value}


def request_supabase(key, action, code, data):
    if not key:
        raise ValueError(
            "Missing GitHub Actions secret OBNOTE_SUPABASE_SECRET_KEY. "
            "Configure it in GitHub repository Settings > Secrets and variables > Actions."
        )
    payload = json.dumps(
        {"p_action": action, "p_code": code, "p_data": data},
        ensure_ascii=False
    ).encode("utf-8")
    request = Request(
        RPC_URL,
        data=payload,
        headers={
            "apikey": key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "OBNOTE-product-manager/1.0"
        },
        method="POST"
    )
    try:
        with urlopen(request, timeout=25) as response:
            return json.load(response)
    except HTTPError as exc:
        response_text = exc.read(1200).decode("utf-8", errors="replace")
        try:
            error = json.loads(response_text)
        except ValueError:
            error = {}
        if isinstance(error, dict) and error.get("code") == "23505":
            problem = str(error.get("message", ""))
            if "obnote_products_name_unique" in problem:
                raise ValueError(
                    "DUPLICATE NAME: A product with this name already exists. "
                    "Edit the existing product instead."
                ) from None
            if "obnote_products_seller_url_unique" in problem:
                raise ValueError(
                    "DUPLICATE SELLER LINK: This purchase URL already belongs "
                    "to another product. Edit the existing listing instead."
                ) from None
            raise ValueError(
                "DUPLICATE PRODUCT: A unique value is already registered."
            ) from None
        if isinstance(error, dict):
            detail = str(error.get("message", "Unknown API error"))[:300]
        else:
            detail = "Unknown API error"
        raise ValueError(
            "Supabase API request failed (HTTP " + str(exc.code) + "): " + detail
        ) from None
    except URLError as exc:
        raise ValueError("Could not reach Supabase: " + str(exc.reason)) from None


def main(action):
    if action not in ("add", "edit", "delete"):
        raise ValueError("Usage: manage_products.py add|edit|delete")

    code = os.getenv("PRODUCT_CODE", "").strip() or None
    data = {}

    if action == "add":
        data = product_payload()
        code = None
    elif action == "edit":
        if not code or not re.fullmatch(r"[A-Za-z0-9-]{1,24}", code):
            raise ValueError("Valid PRODUCT_CODE required")
        field = os.getenv("PRODUCT_FIELD", "").strip()
        data = edit_payload(field, os.getenv("PRODUCT_VALUE", "").strip())
    else:
        if not code or not re.fullmatch(r"[A-Za-z0-9-]{1,24}", code):
            raise ValueError("Valid PRODUCT_CODE required")

    result = request_supabase(
        os.getenv("OBNOTE_SUPABASE_SECRET_KEY", ""),
        action, code, data
    )
    print(
        "OBNOTE " + action + " succeeded for product "
        + str(result.get("code", "?"))
        + " (" + str(result.get("name", "")) + ")"
    )
    if action == "add":
        new_code = str(result.get("code", ""))
        if not re.fullmatch(r"[A-Za-z0-9-]{1,24}", new_code):
            raise ValueError("Database returned an invalid product code")
        github_output = os.getenv("GITHUB_OUTPUT", "")
        if github_output:
            with open(github_output, "a", encoding="utf-8") as output:
                output.write("code=" + new_code + "\n")
        github_summary = os.getenv("GITHUB_STEP_SUMMARY", "")
        if github_summary:
            with open(github_summary, "a", encoding="utf-8") as output:
                output.write("Registered OBNOTE product code: `" + new_code + "`\n")
    return result


if __name__ == "__main__":
    try:
        main(sys.argv[1] if len(sys.argv) > 1 else "")
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print("OBNOTE registration error: " + str(exc), file=sys.stderr)
        sys.exit(1)
