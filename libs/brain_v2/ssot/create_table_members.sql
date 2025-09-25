create table catalog.members (
    member_id      uuid primary key default gen_random_uuid(),
    org_id         text not null,
    full_name      text not null,
    preferred_name text,
    primary_email  text,
    role           text,
    team           text,
    status         text not null default 'active'
    ,created_at    timestamptz not null default now()
    ,updated_at    timestamptz not null default now()
);

create unique index uq_members_org_email
    on catalog.members (org_id, primary_email)
    where primary_email is not null;

create index idx_members_org            on catalog.members (org_id);
create index idx_members_org_status     on catalog.members (org_id, status);
create index idx_members_org_team       on catalog.members (org_id, team);
create index idx_members_org_fullname   on catalog.members (org_id, full_name text_pattern_ops);
