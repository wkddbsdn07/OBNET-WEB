-- OBNOTE duplicate protection, applies to both INSERT and UPDATE.
-- These unique expression indexes also serialize conflicting concurrent writes.
-- Product name normalization: trim, collapse whitespace and compare case-insensitively.
create unique index if not exists obnote_products_name_unique
  on public.products (
    (lower(regexp_replace(btrim(name), '[[:space:]]+', ' ', 'g')))
  );

-- Purchase URL normalization: trim, ignore fragments and trailing slashes,
-- compare case-insensitively; query parameters are preserved.
-- Empty or null purchase URLs are allowed for demo and unlisted items.
create unique index if not exists obnote_products_seller_url_unique
  on public.products (
    (lower(regexp_replace(
      regexp_replace(btrim(purchase_url), '#.*$', ''),
      '/+$', ''
    )))
  )
  where purchase_url is not null and btrim(purchase_url) <> '';

comment on index public.obnote_products_name_unique is
  'Rejects duplicate product names after whitespace and case normalization.';

comment on index public.obnote_products_seller_url_unique is
  'Rejects duplicate nonempty seller URLs, ignoring case, fragments and terminal slashes. Query parameters remain significant.';
