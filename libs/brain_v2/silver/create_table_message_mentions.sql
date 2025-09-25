create table if not exists silver.message_mentions (
    message_id            text not null,
    mention_type          text not null,   -- 'user'|'role'|'channel'|'everyone'|'here'
    mentioned_external_id text,            -- NULL for @everyone/@here
    member_id             uuid,            -- SSOT member if resolvable
    created_at_ts         timestamptz default now(),
    updated_at_ts         timestamptz default now()
);

-- Create the exact unique index ON THE SAME THREE COLUMNS
create unique index if not exists uq_message_mentions
    on silver.message_mentions (message_id, mention_type, mentioned_external_id) nulls not distinct;

create index if not exists idx_message_mentions_member on silver.message_mentions (member_id);