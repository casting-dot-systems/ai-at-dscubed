create table if not exists silver.components (
  org_id text not null,
  system text not null,
  component_id text not null,
  parent_component_id text,
  component_type text not null,
  name text,
  is_active boolean default true,
  created_at_ts timestamptz,
  updated_at_ts timestamptz,
  raw jsonb,
  primary key (system, component_id)
);

create index if not exists idx_components_type on silver.components(component_type);
