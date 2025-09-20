-- Components: channels/threads/etc
create table if not exists silver.components (
  org_id text not null,
  system text not null,                          -- 'discord'
  component_id text not null,                    -- channel_id or thread_id
  parent_component_id text,                      -- parent channel for thread
  component_type text not null,                  -- 'guild_text','thread','forum','voice','category'
  name text,
  is_active boolean default true,
  created_at_ts timestamptz,
  updated_at_ts timestamptz,
  raw jsonb,
  primary key (system, component_id)
);