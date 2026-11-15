#!/usr/bin/env python3
"""Read-only OBNOTE production website and Supabase public API health check.

Checks the actual branded production address, not Vercel's deployment metadata.
Requires no server-side secrets and makes no writes.
"""
from datetime import datetime, timezone
import os
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from catalog_http import fetch_json

HOME = "https://obnote.vercel.app/"
PRIVACY = "https://obnote.vercel.app/privacy.html"
DB = "https://bidcctugofnvfilywick.supabase.co"


def check_page(url, required):
    request = Request(url, headers={"User-Agent": "OBNOTE-health-check/1.0"})
    with urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status} at {url}")
        html = response.read(450_000).decode("utf-8", errors="replace")
    for marker in required:
        if marker not in html:
            raise RuntimeError(f"Expected site content missing at {url}: {marker}")
    return True


def check_public_catalog(api_key):
    if not api_key.startswith("sb_publishable_"):
        raise ValueError("Missing public read-only Supabase key")
    query = urlencode({"select": "code", "published": "eq.true", "limit": 2})
    request = Request(
        DB + "/rest/v1/products?" + query,
        headers={"apikey": api_key, "Accept": "application/json"},
    )
    products = fetch_json(request, timeout=30)
    if not isinstance(products, list):
        raise ValueError("Supabase public catalog did not return a list")
    return len(products)


def main():
    errors = []
    for title, action in (
        ("Branded homepage", lambda: check_page(HOME, ("OBNOTE", 'id="searchForm"'))),
        ("Privacy notice", lambda: check_page(PRIVACY, ("Privacy", "Supabase"))),
        ("Published product API", lambda: check_public_catalog(
            os.environ.get("OBNOTE_SUPABASE_PUBLIC_KEY", "").strip()
        )),
    ):
        try:
            result = action()
            print("PASS:", title, result)
        except Exception as exc:
            print("FAIL:", title, str(exc), file=sys.stderr)
            errors.append(title)

    report = [
        "## OBNOTE production health check",
        "",
        "Checked (UTC): " + datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "Homepage: " + HOME,
        "Result: " + ("PASS" if not errors else "FAIL"),
    ]
    if errors:
        report.append("Failed: " + ", ".join(errors))
    else:
        report.append("Homepage, privacy, and read-only product API are reachable.")
    filename = os.getenv("GITHUB_STEP_SUMMARY")
    if filename:
        with open(filename, "a", encoding="utf-8") as file:
            file.write("\n\n".join(report) + "\n")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
