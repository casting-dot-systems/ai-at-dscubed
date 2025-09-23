create or replace function catalog.ensure_identity_for_discord(_org text, _discord_id text, _hint_name text)
returns void language plpgsql as $$
begin
  insert into catalog.member_identities(member_id, system, external_id)
  values (null, 'discord', _discord_id)
  on conflict (system, external_id) do nothing;
end$$;