-- OBNOTE: secure Supabase products table
-- Preparation only. This has not been executed against a Supabase project.
-- Existing GitHub Pages products.json remains the live source until migration.
-- PostgreSQL / Supabase SQL Editor

create table if not exists public.products (
  code text primary key
    check (code ~ '^[A-Za-z0-9-]{1,24}$'),
  name text not null check (char_length(trim(name)) between 1 and 110),
  category text not null default 'TECH'
    check (char_length(category) <= 40),
  tagline text not null default ''
    check (char_length(tagline) <= 220),
  description text not null default ''
    check (char_length(description) <= 1300),
  features text[] not null default '{}',
  image_url text
    check (image_url is null or image_url ~ '^https://[^[:space:]]+$'),
  price numeric(12,2)
    check (price is null or price > 0),
  currency text not null default 'USD'
    check (currency ~ '^[A-Z]{3}$'),
  purchase_url text
    check (purchase_url is null or purchase_url ~ '^https://[^[:space:]]+$'),
  is_demo boolean not null default true,
  published boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint demo_no_purchase check (
    not is_demo or (purchase_url is null and price is null)
  )
);

create index if not exists products_published_idx
  on public.products (published);

-- API privileges and RLS are independent in Supabase.
-- Anonymous visitors can only read published rows.
-- All writes are restricted to trusted server-side credentials.
alter table public.products enable row level security;

revoke all privileges on table public.products
  from public, anon, authenticated;

grant usage on schema public to anon;
grant select on table public.products to anon;
grant select, insert, update, delete on table public.products
  to service_role;

drop policy if exists "Anyone may read published products" on public.products;
create policy "Anyone may read published products"
  on public.products
  for select to anon
  using (published = true);

-- No public INSERT, UPDATE or DELETE policies.
-- Never expose service_role/secret keys in public JavaScript or GitHub.
