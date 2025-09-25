create or replace function catalog.ensure_member_for_discord(_org text, _discord_id text, _name text)
returns uuid language plpgsql as $$
declare _member_id uuid;
begin
  select mi.member_id into _member_id
  from catalog.member_identities mi
  where mi.system='discord' and mi.external_id=_discord_id;

  if _member_id is null then
    insert into catalog.members(org_id, full_name)
    values (_org, _name) returning member_id into _member_id;

    insert into catalog.member_identities(member_id, system, external_id)
    values (_member_id, 'discord', _discord_id)
    on conflict do nothing;
  else
    update catalog.members set updated_at=now() where member_id=_member_id;
  end if;

  return _member_id;
end$$;
