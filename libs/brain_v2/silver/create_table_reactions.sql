create table if not exists silver.reactions (
    message_id text references silver.messages(message_id) on delete cascade not null,
    reaction text not null,
    member_id uuid,
    created_at_ts timestamptz default now()

);

create index if not exists idx_reactions_message on silver.reactions (message_id);
create index if not exists idx_reactions_member on silver.reactions (member_id);