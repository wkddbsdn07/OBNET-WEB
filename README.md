# OBNOTE Website

An English-language technology and desk-accessory product discovery prototype.

**Public branded website:** https://obnote.vercel.app/

**Architecture:** Vercel presents the public branded URL using an external rewrite to the unchanged GitHub Pages origin (`https://wkddbsdn07.github.io/OBNET-WEB/`). This preserves updates to the existing GitHub site without requiring a new Git integration or changing the GitHub account. Do not add a client-side redirect at the origin, as it would redirect the proxied site too.

## Current architecture

- **GitHub Pages:** hosts `index.html` and `privacy.html`.
- **Supabase (Seoul project `bidcctugofnvfilywick`):** authoritative product database.
- **Public visitors:** read published products only, using a publishable key. Row-level security (RLS) denies public changes.
- **Product administrators:** add, edit, or delete via privileged backend APIs only. The static website contains **no secret credentials**.
- **`products.json`:** legacy demo backup, **not the active catalog**. Changing it will no longer update the website.
- **`scripts/add_product.py`:** previous JSON-only numbering tool, kept for history/testing; do not use it to publish new products.

## Product management: first-time GitHub setup

The database and protected CRUD RPC function `public.obnote_manage_product` are installed and passed a create/edit/delete smoke test. GitHub Actions management workflows require one GitHub repository secret **before they can run**:

1. Open [OBNOTE Supabase API Keys](https://supabase.com/dashboard/project/bidcctugofnvfilywick/settings/api-keys). Create or obtain a server-side **secret key** (`sb_secret_...`, not a publishable key).
2. Open [Add GitHub Actions secret](https://github.com/wkddbsdn07/OBNET-WEB/settings/secrets/actions/new).
3. Set **Name** to `OBNOTE_SUPABASE_SECRET_KEY` and **Secret** to the server-side secret key; save it.

**Never paste the secret into chat, README, a commit, website JavaScript, or GitHub workflow inputs.** Keep it only in GitHub Actions Secrets or a secure backend credential store.

## Add / edit / delete from phone or browser

Once the secret is configured:

- **Add:** [Add OBNOTE product](https://github.com/wkddbsdn07/OBNET-WEB/actions/workflows/add-product.yml) → Run workflow. Enter name, description and optional fields. The server generates a sequential unique product code.
- **Edit:** [Edit OBNOTE product](https://github.com/wkddbsdn07/OBNET-WEB/actions/workflows/edit-product.yml) → Run workflow. Supply code, a field, and new value. Change one field per run. For `features`, separate items with `|`. Set `published` to `false` to hide an item.
- **Delete:** [Delete OBNOTE product](https://github.com/wkddbsdn07/OBNET-WEB/actions/workflows/delete-product.yml) → Run workflow. Supply the code; deletion permanently removes the database item.

Updates appear through the Supabase Data API without a GitHub Pages rebuild. Editing an item to `is_demo=true` while it has price/purchase URL requires clearing those fields first. Demo products do not expose live purchase links or verified prices.

**Status:** The backend and GitHub Actions secret were tested with a temporary unpublished product: create, edit and delete all passed. Individual add/edit/delete buttons are operational workflows; actual real-product registration requires verified product information.

## Code and database security

Database DDL: `supabase/schema.sql` and `supabase/product-management.sql`; initial demo import: `supabase/seed-demo.sql`. The management RPC is `SECURITY INVOKER` and executable only by `service_role`. A dedicated internal sequence allocates product codes without collisions. Do not expose service-role/secret keys to site visitors.

**Testing:** `python3 -m unittest discover -s tests -v`. The GitHub Actions test workflow checks CLI input validation and the old numbering helper. Database-level create/edit/delete and role privilege tests were also run separately.

This GitHub Pages deployment is a non-commercial demo. Check hosting and affiliate program terms before commercial use.

## Duplicate listing protection

Supabase now enforces uniqueness for **product names** and **seller URLs**, for both additions and edits. These are atomic database unique indexes, so concurrent submissions cannot create an exact normalized duplicate. SQL is in `supabase/prevent-duplicate-products.sql`. A duplicate submission fails with a friendly **DUPLICATE NAME** or **DUPLICATE SELLER LINK** message in GitHub Actions.

Normalization: names ignore casing, leading/trailing spaces, and repeated whitespace. Seller URLs ignore casing, fragments (`#...`) and trailing slashes. Query parameters (`?...`) remain significant, so tracking-URL variants and differently named listings may still need human review. Blank seller URLs are allowed. Product codes stay unique using the existing primary key.

## Stock / price review dates and history

The site displays administrator-reported stock status (`unknown`, `in_stock`, `out_of_stock`, or `preorder`) and recorded review dates. Admins update the `stock_status` or `price` field from the Edit OBNOTE product workflow. Changes to price, currency or stock status are archived in the private `obnote_internal.product_change_history` table; visitors cannot read that history.

The [daily audit](.github/workflows/audit-catalog.yml) runs at **09:07 KST** and flags real published listings with missing or older-than-seven-day review timestamps. It does **not** access seller websites and cannot verify live price or inventory. The four demo items are excluded from audits.

## Shorts previews

[Render OBNOTE Shorts template](.github/workflows/render-short.yml) accepts any published product code and produces a **silent** 1080×1920 MP4, original fact-limited English narration JSON, and an SRT subtitle file in a downloadable GitHub Actions artifact. It never uploads to YouTube. The clip uses self-created geometric graphics and type only: no third-party photographs, copyrighted music or guessed product claims. Demo items are visibly labeled as fictional. [Video renderer](scripts/render_short.py), [narration generator](scripts/generate_short_script.py).

**31-item tracking:** [ROADMAP.md](ROADMAP.md).

## Automated Shorts drafts (no YouTube publishing)

Each **Add OBNOTE product** workflow now has an enabled-by-default `render_draft` option. When the product is successfully registered, GitHub Actions passes its newly assigned code into the reusable [Render OBNOTE Shorts template](.github/workflows/render-short.yml) workflow. The workflow produces:

- Original **1080×1920 MP4 with in-frame captions and offline English eSpeak NG narration**
- A silent backup MP4
- Original fact-limited narration JSON + SRT subtitle file
- An English YouTube title and description **draft**, including a product code URL on `obnote.vercel.app`
- A downloadable GitHub Actions artifact, retained for seven days

The reuse mechanism was verified end-to-end with a fictional demo item in [Verify OBNOTE auto-draft pipeline](.github/workflows/verify-reusable-render.yml). The separate GitHub product registration and generation chain is wired, but a real product has not yet been registered. No YouTube channel OAuth or automatic video publishing is enabled.

The offline voice is understandable but intentionally basic, not a commercial-grade neural voice. The renderer draws original graphic shapes and text; it does not download third-party product photos or claim to have tested products. Concept demo footage is labeled clearly.

## Failure handling

The public catalog fetcher uses [temporary-error retries](scripts/catalog_http.py) for HTTP 408/429/5xx and network outages. Permission and missing-item errors do not retry. Failed jobs show GitHub Actions errors and logs.

[Notify OBNOTE workflow failure](.github/workflows/notify-failure.yml) observes failures of the core product, Shorts and freshness workflows. If the optional secret `OBNOTE_DISCORD_WEBHOOK` is set in **GitHub Actions Secrets**, a simple message with the failed Actions run link can also be sent to Discord. Without that secret, no external alert is sent. A Discord webhook secret must **never** be committed or pasted into the public site.

These are **drafts and diagnostics**, not automatic advertising or monetization.
