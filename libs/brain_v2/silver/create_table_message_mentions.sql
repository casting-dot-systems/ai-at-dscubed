create table if not exists silver.message_mentions (
    message_id            text not null,
    mention_type          text not null, 
    mentioned_external_id text,
    member_id             uuid, 
    created_at_ts         timestamptz default now(),
    updated_at_ts         timestamptz default now()
);

create unique index if not exists uq_message_mentions
    on silver.message_mentions (message_id, mention_type, mentioned_external_id) nulls not distinct;
