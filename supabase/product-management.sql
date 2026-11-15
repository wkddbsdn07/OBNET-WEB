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
      image_url, price, currency, purchase_url, is_demo, published
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
      coalesce((v_data->>'published')::boolean,false)
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
