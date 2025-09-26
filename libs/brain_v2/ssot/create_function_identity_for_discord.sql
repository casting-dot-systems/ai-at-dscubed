CREATE OR REPLACE FUNCTION CATALOG.ENSURE_IDENTITY_FOR_DISCORD (
    P_ORG_ID TEXT,
    P_EXTERNAL_ID TEXT,
    P_EXTERNAL_USERNAME TEXT
) RETURNS UUID LANGUAGE PLPGSQL AS $$
declare
    v_identity_id uuid;
begin
    insert into catalog.member_identities (org_id, system, external_id, external_username)
    values (p_org_id, 'discord', p_external_id, p_external_username)
    on conflict (system, external_id) do update
        set external_username = excluded.external_username,
            updated_at        = now()
    returning member_identity_id into v_identity_id;

    return v_identity_id;
end;
$$;
