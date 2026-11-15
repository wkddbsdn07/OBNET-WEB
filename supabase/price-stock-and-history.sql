-- Fields represent administrator-reported values; this does not scrape seller websites.
alter table public.products
  add column if not exists stock_status text not null default 'unknown',
  add column if not exists price_checked_at timestamptz,
  add column if not exists stock_checked_at timestamptz;

alter table public.products
  add constraint obnote_stock_status_valid
  check (stock_status in ('unknown', 'in_stock', 'out_of_stock', 'preorder'));

alter table public.products
  add constraint obnote_demo_stock_unknown
  check (not is_demo or stock_status = 'unknown');

create table if not exists obnote_internal.product_change_history (
  id bigint generated always as identity primary key,
  product_code text not null,
  old_price numeric(12,2),
  new_price numeric(12,2),
  old_currency text,
  new_currency text,
  old_stock_status text,
  new_stock_status text,
  changed_at timestamptz not null default now(),
  action text not null check (action in ('created','changed'))
);

revoke all on obnote_internal.product_change_history from public, anon, authenticated;
grant select, insert on obnote_internal.product_change_history to service_role;
grant usage, select on sequence obnote_internal.product_change_history_id_seq to service_role;
alter table obnote_internal.product_change_history enable row level security;

create or replace function obnote_internal.capture_product_changes()
returns trigger language plpgsql security invoker set search_path = ''
as $audit$
begin
  if tg_op = 'INSERT' then
    if new.price is not null or new.stock_status <> 'unknown' then
      insert into obnote_internal.product_change_history
        (product_code,new_price,new_currency,new_stock_status,action)
      values (new.code,new.price,new.currency,new.stock_status,'created');
    end if;
  elsif old.price is distinct from new.price
      or old.currency is distinct from new.currency
      or old.stock_status is distinct from new.stock_status then
    insert into obnote_internal.product_change_history
      (product_code,old_price,new_price,old_currency,new_currency,
       old_stock_status,new_stock_status,action)
    values (new.code,old.price,new.price,old.currency,new.currency,
            old.stock_status,new.stock_status,'changed');
  end if;
  return new;
end
$audit$;
revoke all on function obnote_internal.capture_product_changes() from public, anon, authenticated;
grant execute on function obnote_internal.capture_product_changes() to service_role;
drop trigger if exists obnote_track_product_changes on public.products;
create trigger obnote_track_product_changes
  after insert or update on public.products
  for each row execute function obnote_internal.capture_product_changes();

-- OBNOTE product CRUD API (server-side only, never expose a secret key in a browser)
-- API callable exclusively as service_role. The site uses a publishable read-only key.
-- Unique product numbers come from a PostgreSQL sequence.
create schema if not exists obnote_internal;
revoke all on schema obnote_internal from public, anon, authenticated;
grant usage on schema obnote_internal to service_role;

create sequence if not exists obnote_internal.product_code_seq
  as bigint start with 1005 minvalue 1005;
revoke all on sequence obnote_internal.product_code_seq from public, anon, authenticated;
grant usage, select on sequence obnote_internal.product_code_seq to service_role;

create or replace function public.obnote_manage_product(
  p_action text,
  p_code text default null,
  p_data jsonb default '{}'::jsonb
)
returns jsonb
language plpgsql
security invoker
set search_path = ''
as $function$
declare
  v_item public.products%rowtype;
  v_code text;
  v_data jsonb := coalesce(p_data, '{}'::jsonb);
  v_features text[];
begin
  if p_action not in ('add','edit','delete') or p_action is null then
    raise exception 'Unsupported action (use add, edit or delete)';
  end if;

  if p_action = 'add' then
    if nullif(btrim(v_data->>'name'), '') is null
      or nullif(btrim(v_data->>'description'), '') is null then
      raise exception 'Name and description are required';
    end if;
    if v_data ? 'features' and jsonb_typeof(v_data->'features') <> 'array' then
      raise exception 'Features must be an array';
    end if;
    select coalesce(array_agg(x), '{}'::text[])
      into v_features from jsonb_array_elements_text(
        case when jsonb_typeof(v_data->'features') = 'array'
          then v_data->'features' else '[]'::jsonb end
      ) as f(x);

    v_code := nextval('obnote_internal.product_code_seq')::text;
    insert into public.products(
      code, name, category, tagline, description, features,
      image_url, price, currency, purchase_url, is_demo, published,
      stock_status, price_checked_at, stock_checked_at
    )
    values (
      v_code,
      btrim(v_data->>'name'),
      coalesce(nullif(btrim(v_data->>'category'),''),'TECH'),
      coalesce(v_data->>'tagline',''),
      btrim(v_data->>'description'),
      v_features,
      nullif(v_data->>'image_url',''),
      nullif(v_data->>'price','')::numeric,
      coalesce(nullif(upper(v_data->>'currency'),''),'USD'),
      nullif(v_data->>'purchase_url',''),
      coalesce((v_data->>'is_demo')::boolean,true),
      coalesce((v_data->>'published')::boolean,false),
      coalesce(nullif(v_data->>'stock_status',''),'unknown'),
      case when coalesce((v_data->>'is_demo')::boolean,true)=false and nullif(v_data->>'price','') is not null then now() else null end,
      case when coalesce((v_data->>'is_demo')::boolean,true)=false and coalesce(nullif(v_data->>'stock_status',''),'unknown')<>'unknown' then now() else null end
    )
    returning * into v_item;

  elsif p_action = 'edit' then
    if nullif(btrim(p_code), '') is null then
      raise exception 'Product code is required for edit';
    end if;
    if v_data ? 'features' and jsonb_typeof(v_data->'features') <> 'array' then
      raise exception 'Features must be an array';
    end if;
    if v_data ? 'features' then
      select coalesce(array_agg(x), '{}'::text[]) into v_features
      from jsonb_array_elements_text(v_data->'features') as f(x);
    end if;
    update public.products set
      name = case when v_data ? 'name' then btrim(v_data->>'name') else name end,
      category = case when v_data ? 'category' then btrim(v_data->>'category') else category end,
      tagline = case when v_data ? 'tagline' then coalesce(v_data->>'tagline','') else tagline end,
      description = case when v_data ? 'description' then coalesce(v_data->>'description','') else description end,
      features = case when v_data ? 'features' then v_features else features end,
      image_url = case when v_data ? 'image_url' then nullif(v_data->>'image_url','') else image_url end,
      price = case when v_data ? 'price' then nullif(v_data->>'price','')::numeric else price end,
      currency = case when v_data ? 'currency' then upper(v_data->>'currency') else currency end,
      purchase_url = case when v_data ? 'purchase_url' then nullif(v_data->>'purchase_url','') else purchase_url end,
      is_demo = case when v_data ? 'is_demo' then (v_data->>'is_demo')::boolean else is_demo end,
      published = case when v_data ? 'published' then (v_data->>'published')::boolean else published end,
      stock_status = case when v_data ? 'stock_status' then coalesce(nullif(v_data->>'stock_status',''),'unknown') else stock_status end,
      price_checked_at = case when v_data ? 'price' or v_data ? 'currency' then case when nullif(coalesce(v_data->>'price', price::text),'') is not null then now() else null end else price_checked_at end,
      stock_checked_at = case when v_data ? 'stock_status' then case when coalesce(nullif(v_data->>'stock_status',''),'unknown') <> 'unknown' then now() else null end else stock_checked_at end,
      updated_at = now()
    where code = p_code returning * into v_item;

  else
    if nullif(btrim(p_code), '') is null then
      raise exception 'Product code is required for delete';
    end if;
    delete from public.products where code = p_code returning * into v_item;
  end if;

  if not found then
    raise exception 'Product code not found: %', coalesce(p_code, '?');
  end if;
  return jsonb_build_object(
    'action',p_action,'code',v_item.code,'name',v_item.name,'published',v_item.published
  );
end
$function$;

-- Functions default to execute-by-public. Revoke before granting only service_role.
revoke all on function public.obnote_manage_product(text,text,jsonb) from public, anon, authenticated;
grant execute on function public.obnote_manage_product(text,text,jsonb) to service_role;
