create table if not exists catalog.members (
  member_id uuid primary key default gen_random_uuid(),
  org_id text not null,
  full_name text,
  preferred_name text,
  primary_email text,
  role text,
  team text,
  status text check (status in ('active','inactive')) default 'active',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);