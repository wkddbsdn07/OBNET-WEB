# OBNOTE Website

OBNOTE is an English-language technology and desk-accessory discovery demo, hosted on GitHub Pages.

## Managing products

Product information is stored in `products.json` rather than inside the website code. Each entry needs a unique `code` and `name`. The site renders the cards and detail views from that data.

Example structure for a future, verified listing:

```json
{
  "code": "1004",
  "name": "Product name",
  "category": "DESK TECH",
  "tagline": "Short introduction",
  "description": "Your original product description.",
  "features": ["Key feature", "Another feature"],
  "image_url": "https://example.com/authorized-photo.jpg",
  "price": 29.99,
  "currency": "USD",
  "purchase_url": "https://example.com/product",
  "is_demo": false
}
```

The above is an example record, not a real product. Add it to the existing JSON array, separating records with commas.

- Use `null` for unknown price, missing photo, or unavailable purchase link.
- The current products 1001–1003 are fictional demos. They are marked `is_demo: true`, and purchase links stay disabled.
- Only use product images and promotional material you have permission to publish, and verify product specifications and prices.
- Only use affiliate links permitted by the platform, your account eligibility and the site's rules; disclose affiliate relationships.
- NEVER store passwords, personal information, GitHub tokens or API keys in these public files.

## How it works

`index.html` is static and loads `products.json` in the browser. It can work without a personal server or VPS. For a future secure product management dashboard with shared editing, use a backend and authentication rather than exposing credentials in frontend code.

This GitHub Pages site is a non-commercial prototype. Commercial affiliate website hosting may require migration to an appropriate provider.


## Registering a product: automatic code assignment

Use **GitHub → Actions → Add OBNOTE product → Run workflow** in the repository.

1. Enter the required product **name**, **category**, and **description**.
2. Optionally enter a tagline and features separated by a pipe (`USB-C | Compact`).
3. Use an approved HTTPS image URL only if you have permission to publish the image.
4. Keep **Demo product** checked for tests. It automatically removes purchase URLs and prices.
5. Click **Run workflow** once. GitHub Actions reads the latest `products.json`, assigns the next unique sequential code (`1004`, then `1005`, etc.), checks for duplicates and unsafe URLs, commits the new listing, and explicitly requests a GitHub Pages rebuild.

**Where to find the code:** Open the workflow run's "Allocate product code and register product" step; it prints `Registered product code: 1004` (or the next available number). You can also view the new record in `products.json`.

This workflow requires GitHub Actions write permission to commit catalog changes and Pages write permission to request a rebuild. If the workflow fails, inspect the run's error details; the product may have been committed even if the later Pages rebuild request fails. The first end-to-end registration run is not yet verified.

**Local CLI (for future Hermes automation):**

```sh
python3 scripts/add_product.py --name "Test Desk Dock" --category "DESK TECH" --description "Demo product description" --is-demo true
```

Do not publish personal access tokens or any other credentials in the website, catalog, or workflow inputs.

**Tests:** `python3 -m unittest discover -s tests -v` (runs automatically on test/script updates).

