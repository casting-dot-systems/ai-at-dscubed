-- Mentions (optional)
create table if not exists silver.message_mentions (
  message_id text references silver.messages(message_id) on delete cascade,
  mention_type text,                             -- 'user'|'role'|'channel'
  mentioned_external_id text,
  primary key (message_id, mention_type, mentioned_external_id)
);