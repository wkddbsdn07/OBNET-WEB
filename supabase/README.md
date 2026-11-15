# OBNOTE × Supabase — prepared integration

Status: **NOT CONNECTED YET**. This repository currently has a working GitHub Pages website that reads `products.json`. Do not remove that fallback until the database has been created and tested.

## Why Supabase?

We want a central product catalog that can eventually support a secure editor, stock and price tracking, and automated publication by Hermes. This must not expose administrative credentials to public website visitors.

## Database setup

1. Create an appropriate Supabase project in the chosen organization. Review project pricing and account eligibility before creation.
2. Apply `schema.sql` to define `public.products`, database checks, published-only public SELECT policy, and no public writes.
3. Apply `seed-demo.sql` to import the four fictional demonstration products, codes 1001 to 1004. The seed leaves existing records untouched.
4. Verify the four codes via SQL and review Supabase's Security Advisor.
5. Retrieve the project URL and a **publishable** API key. A publishable key can be used by public browser JavaScript **only with correct RLS**, and must never be confused with secret or service-role keys.
6. After confirming the database works, update the website to read published products from the read-only Data API. Keep `products.json` as a temporary fallback during cutover.

## Security model

- Public users can **SELECT published products only**, not insert, update, or delete.
- There is no login or write interface on the public static site.
- GitHub Actions should only gain database write access through a properly managed secret stored in GitHub Actions Secrets (not committed to this repository). Never send the service-role key to frontend code.
- Product codes are currently allocated by the GitHub Actions workflow against `products.json`. Before treating Supabase as the canonical product store, we must implement one authoritative allocator to avoid GitHub/Supabase code collisions.
- Current demo products are fictional, not real offers. Display real product images and purchase links only with permission and correct disclosures.

## Current checklist state

Site: running on GitHub Pages. Product registration and code generation: tested in GitHub Actions. Supabase project: none was available to the connected account when these files were prepared, so **the database is not yet running**.
