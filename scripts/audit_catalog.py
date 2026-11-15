#!/usr/bin/env python3
"""Daily OBNOTE catalog freshness audit.

Reads only public, published Supabase product data. It never scrapes sellers,
never changes a listing, and does not need an administrative secret.
Non-demo listings with unknown/stale stock data or stale listed prices fail
the workflow so their owners can review the original sellers manually.
"""
from datetime import datetime, timedelta, timezone
import json
import os
import sys
from urllib.request import Request, urlopen

DB = "https://bidcctugofnvfilywick.supabase.co"
FIELDS = "code,name,is_demo,price,price_checked_at,stock_status,stock_checked_at"
STALE_DAYS = 7


def parsed_time(value):
    if not value:
        return None
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return timestamp.replace(tzinfo=timezone.utc) if not timestamp.tzinfo else timestamp.astimezone(timezone.utc)
    except ValueError:
        return None


def find_issues(products, now=None):
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=STALE_DAYS)
    issues = []
    count = 0
    for p in products:
        if p.get("is_demo", False):
            continue
        count += 1
        code = str(p.get("code", "?"))
        stock = p.get("stock_status", "unknown")
        stock_date = parsed_time(p.get("stock_checked_at"))
        if stock not in ("in_stock", "out_of_stock", "preorder") or stock_date is None:
            issues.append((code, "Stock availability not reviewed"))
        elif stock_date < cutoff:
            issues.append((code, "Stock availability last reviewed more than 7 days ago"))
        price = p.get("price")
        if price is not None:
            price_date = parsed_time(p.get("price_checked_at"))
            if price_date is None:
                issues.append((code, "Listed price has no recorded review date"))
            elif price_date < cutoff:
                issues.append((code, "Listed price last reviewed more than 7 days ago"))
    return count, issues


def main():
    key = os.environ.get("OBNOTE_SUPABASE_PUBLIC_KEY", "").strip()
    if not key.startswith("sb_publishable_"):
        print("Missing publishable key for catalog audit", file=sys.stderr)
        return 2
    from urllib.parse import urlencode
    endpoint = DB + "/rest/v1/products?" + urlencode({
        "select": FIELDS, "published": "eq.true", "order": "code.asc"
    })
    request = Request(endpoint, headers={"apikey": key, "Accept": "application/json"})
    with urlopen(request, timeout=25) as response:
        products = json.load(response)
    if not isinstance(products, list):
        raise ValueError("Expected a list of published products")

    count, issues = find_issues(products)
    lines = [
        "## OBNOTE product freshness audit",
        "",
        "Published real products checked: " + str(count),
        "Items requiring manual seller review: " + str(len(set(code for code, _ in issues))),
        "",
    ]
    if not count:
        lines.append("No real products are published yet; demo entries are excluded.")
    if issues:
        lines.append("This audit checks **record age only**, not live seller inventory or price.")
        for code, reason in issues:
            lines.append("- Product " + code + ": " + reason)
    else:
        lines.append("No missing or stale review timestamps found in published real items.")

    report = "\n".join(lines) + "\n"
    print(report)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fp:
            fp.write(report)
    return 1 if issues else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("Audit could not run: " + str(exc), file=sys.stderr)
        sys.exit(2)
