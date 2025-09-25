create or replace view catalog.v_members_active as
select *
from catalog.members
where status = 'active';