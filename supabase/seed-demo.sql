-- OBNOTE: one-time import of demo catalog after supabase/schema.sql
-- Demonstration products only. Safe to re-run: existing codes are preserved.
-- Real seller links and prices are intentionally absent.

insert into public.products (
  code, name, category, tagline, description, features,
  image_url, price, currency, purchase_url, is_demo, published
)
values
  ('1001', 'Orbit Dock', 'DESK TECH', 'A cleaner desk, by design.', 'A concept desktop dock demonstrating how a product page could introduce elegant cable organization and workspace essentials.', ARRAY['Concept product for interface testing','Geometric desktop accessory visualization','No actual listing or price']::text[], NULL, NULL, 'USD', NULL, true, true),
  ('1002', 'Halo Light', 'WORKSPACE', 'Light the way you work.', 'A conceptual ambient desk lamp entry designed to demonstrate a futuristic lighting product presentation.', ARRAY['Concept product for interface testing','Soft circular light form','No actual listing or price']::text[], NULL, NULL, 'USD', NULL, true, true),
  ('1003', 'Modular Grid', 'DESK ACCESSORIES', 'Find room for better ideas.', 'A concept modular organizer entry showing how small geometric objects can make a digital product catalog feel cohesive.', ARRAY['Concept product for interface testing','Stackable geometric arrangement','No actual listing or price']::text[], NULL, NULL, 'USD', NULL, true, true),
  ('1004', 'Test Desk Stand', 'DESK TECH', '', 'Demo product for testing', ARRAY[]::text[], NULL, NULL, 'USD', NULL, true, true)
on conflict (code) do nothing;

-- Verification query after import:
select code, name, is_demo, published
from public.products
order by code;
