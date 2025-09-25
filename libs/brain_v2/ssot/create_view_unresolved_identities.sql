create or replace view catalog.v_unresolved_identities as
select
    member_identity_id,
    org_id,
    system,
    external_id,
    external_username,
    created_at,
    updated_at
from catalog.member_identities
where member_id is null
order by updated_at desc;
