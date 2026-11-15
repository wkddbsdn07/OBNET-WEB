# OBNOTE Project Roadmap

**Status:** 14 / 31 checklist items complete (45.2%) as of November 15, 2026.

This is a prototype roadmap. Done means the core function has been built and tested; this does not mean commercial readiness or that real product content has been licensed.

## 1. Foundation — 3 / 4

- [x] Create the OBNOTE YouTube channel
- [x] Choose channel name, logo, and banner
- [ ] Review affiliate-program eligibility and account requirements — defer until eligible
- [x] Choose IT gadgets + innovative desk-tech category

## 2. Website — 4 / 6

- [ ] Migrate to Next.js — optional; current static website works
- [x] Product code search
- [x] Product photo, description, price, and optional seller-link UI
- [x] Mobile layout verification
- [x] Privacy / affiliate disclosures
- [ ] Vercel deployment — optional; GitHub Pages currently works

## 3. Product management — 4 / 5

- [x] Automatic sequential product codes in Supabase
- [x] Supabase product database and read-only public API
- [x] Server-side product add / edit / delete
- [x] Atomic duplicate-name and duplicate-seller-link prevention
- [ ] Verify actual seller stock and price changes automatically. **Partially built:** administrator-reported stock/price, private change history, and scheduled stale-record audit. No actual third-party seller check until real approved seller URLs and reliable integration exist.

## 4. Shorts content — 3 / 6

- [x] Branded 1080×1920 silent video template renderer
- [x] Automatic fact-limited English script + subtitle text generator — deterministic template (AI writing upgrade is pending)
- [ ] Collect properly licensed product photo/video assets
- [ ] Automatically synthesize voice, subtitles and final audio/video (silent video + separate SRT are available)
- [x] Show product number on final Shorts scene
- [ ] Add appropriate sponsorship/affiliate disclosure to real promotional videos

## 5. Automation — 0 / 5

- [ ] Connect Hermes Agent with the approved product management APIs
- [ ] Automatically register product and generate real videos
- [ ] Automatically upload videos to YouTube (requires authorized channel connection)
- [ ] Implement retries and alerting for the full publication pipeline
- [ ] Schedule real product video creation and publication

**Already automated:** GitHub Actions daily review-date audit (09:07 KST) and manual product/video workflows. These do **not** imply unattended content publishing.

## 6. Analytics and monetization — 0 / 5

- [ ] PostHog analytics with transparent privacy disclosures
- [ ] YouTube views / incoming traffic analytics
- [ ] Eligible account setup and actual payouts
- [ ] Track real affiliate commission revenue
- [ ] Use verified popular products to inform future content

## Verified building blocks

- [Public OBNOTE address](https://obnote.vercel.app/) — Vercel reverse-proxies GitHub Pages to keep the website current without changing the GitHub username. The site reads published Supabase products.
- [Product administration](.github/workflows/add-product.yml), [edit](.github/workflows/edit-product.yml), [delete](.github/workflows/delete-product.yml) — secret-backed actions.
- [Daily price/stock record audit](.github/workflows/audit-catalog.yml) — verifies **review dates**, not real-time seller stock.
- [Branded silent video + narration/subtitle generator](.github/workflows/render-short.yml) — generates a downloadable Actions artifact using a published product code.
- [Tests](.github/workflows/test-product-codes.yml) — catalog, UI script syntax, stock audit, and narration tests.

**Safety:** No real product claims, prices, affiliate status, copyrighted photos, or ad income should be invented. The 1001–1004 items remain fictional demos. Administrative keys are stored only in GitHub Actions Secrets, never in the website.
