create table if not exists catalog.member_identities (
  identity_id uuid primary key default gen_random_uuid(),
  member_id uuid references catalog.members(member_id) on delete cascade,
  system text not null,                 -- 'discord'
  external_id text not null,            -- discord user id (snowflake)
  unique(system, external_id)
);