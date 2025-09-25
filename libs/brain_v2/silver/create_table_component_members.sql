create table if not exists silver.component_members (
  system text not null,
  component_id text not null,
  external_id text not null,
  member_id uuid,
  can_view boolean not null default true,
  org_id text not null,
  updated_at_ts timestamptz not null default now(),
  primary key (system, component_id, external_id)
);

create index if not exists idx_component_members_component
  on silver.component_members(system, component_id);