-- Explicit private history access policy.
-- This table is in non-exposed obnote_internal, schema/table grants
-- continue to block anon and authenticated roles.
create policy "Backend can read and append product history"
  on obnote_internal.product_change_history
  for all to service_role
  using (true)
  with check (true);
