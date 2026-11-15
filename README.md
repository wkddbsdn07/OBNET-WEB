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
