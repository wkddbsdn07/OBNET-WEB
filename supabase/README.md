# OBNOTE — Supabase integration

Status: **CONNECTED** (Supabase project: `bidcctugofnvfilywick`, Seoul).

**Public product API:** `https://bidcctugofnvfilywick.supabase.co/rest/v1/products`

## Applied SQL

1. `schema.sql` — `public.products`, public read-only RLS, no public write privileges.
2. `seed-demo.sql` — imported demo products 1001–1004.
3. `product-management.sql` — internal code sequence starting at 1005 and protected add/edit/delete RPC, executed only by the `service_role` database role.

The CRUD smoke test created a temporary unpublished product, edited it and deleted it. **The test consumed code 1005** (sequences do not reclaim issued values), so the next allocation should be **1006** if nothing else is registered.

## Catalog source of truth

The browser reads **Supabase** as the sole live product catalog, so deleted or unpublished items cannot reappear from an out-of-date `products.json`. The JSON file is a historical backup only.

The public database key in `index.html` is a publishable key and is permitted in frontend code only because RLS restricts reading to `published=true` products. Neither GitHub Pages nor the frontend has a secret or service-role key.

## GitHub Actions integration

Repository workflows:

- `.github/workflows/add-product.yml`
- `.github/workflows/edit-product.yml`
- `.github/workflows/delete-product.yml`

All use `scripts/manage_products.py` and need the **GitHub Actions secret** named `OBNOTE_SUPABASE_SECRET_KEY` containing a server-side Supabase secret key (`sb_secret_...`). Without it the workflows fail safely and do not change the catalog.

The existing Connected Supabase plugin allows database administration through authorized tool actions without adding this GitHub secret, but the mobile GitHub Actions buttons require the one-time secret setup. NEVER copy a secret into a public file or chat.

## Security

The management RPC in `public` uses `SECURITY INVOKER`, not `SECURITY DEFINER`; EXECUTE has been revoked from PUBLIC/anon/authenticated and granted only to service_role. The internal sequence is in a non-exposed schema.

For production use, periodically check the Supabase Security Advisor and keep the commercial hosting and affiliate restrictions in mind.

## Duplicate protection

Applied migration: `prevent-duplicate-products.sql`. Two unique indexes prevent duplicate product names or seller links on both INSERT and UPDATE, even with simultaneous requests.

- Product names are matched case-insensitively, ignoring repeated and surrounding whitespace.
- Seller URLs are matched case-insensitively, ignoring `#` fragments and trailing slashes. Query parameters remain significant.
- Missing seller links do not count as duplicates.
- This is not fuzzy duplicate detection; similar names and different tracked URLs may still refer to the same product.

Verified using SQL insert/update collision assertions inside a rolled-back transaction. Existing products were not changed.

## Price and inventory tracking migrations

Applied in this order after the initial catalog and CRUD table:
1. `prevent-duplicate-products.sql` — unique normalized product names and seller URLs.
2. `price-stock-and-history.sql` — reported `stock_status` and review timestamps, private history table, update trigger, updated management RPC.
3. `fix-price-check-on-clear.sql` — clearing a price also clears the recorded price review timestamp.
4. `private-history-access-policy.sql` — explicit backend-only policy for private history.

The private table is **not** exposed to public Data API visitors. Existing demo items retain `unknown` status and no price. Do not reapply the older `product-management.sql` afterward, as it describes the original pre-stock version of the RPC.

The catalog audit reports records needing seller review; it does not fetch or verify real seller stock.
