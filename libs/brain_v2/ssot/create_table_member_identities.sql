create table catalog.member_identities (
    member_identity_id uuid primary key default gen_random_uuid(),
    org_id text not null,
    member_id uuid references catalog.members(member_id) on delete set null,
    system text not null,
    external_id text not null,
    external_username text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create unique index uq_member_identities_system_external
    on catalog.member_identities (system, external_id);

create index idx_member_identities_system_username
    on catalog.member_identities (system, external_username text_pattern_ops);