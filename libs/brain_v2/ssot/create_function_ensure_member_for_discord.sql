CREATE OR REPLACE FUNCTION CATALOG.ENSURE_MEMBER_FOR_DISCORD (
    P_ORG_ID TEXT,
    P_EXTERNAL_ID TEXT,
    P_EXTERNAL_USERNAME TEXT
) RETURNS UUID LANGUAGE PLPGSQL AS $$
declare
    v_member_id uuid;
begin
    -- First, ensure identity row exists (if not present)
    insert into catalog.member_identities (org_id, system, external_id, external_username)
    values (p_org_id, 'discord', p_external_id, p_external_username)
    on conflict (system, external_id) do update
        set external_username = excluded.external_username,
            updated_at        = now()
    returning member_id into v_member_id;

    -- At this point:
    -- - If identity was already linked, v_member_id will be non-null
    -- - If identity is new or unlinked, v_member_id will be null

    return v_member_id;
end;
$$;