-- Messages (one row per message)
create table if not exists silver.messages (
  org_id text not null,
  system text not null,                          -- 'discord'
  message_id text primary key,
  component_id text not null,                    -- channel/thread where it lives
  author_external_id text not null,              -- discord user id
  author_member_id uuid,                         -- resolved SSOT id
  content text,
  has_attachments boolean default false,
  reply_to_message_id text,
  created_at_ts timestamptz,
  edited_at_ts timestamptz,
  deleted_at_ts timestamptz,
  raw jsonb
);