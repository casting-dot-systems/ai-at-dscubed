create or replace view catalog.v_members_by_team as
select org_id, team, count(*) as member_count
from catalog.members
group by org_id, team
order by org_id, team;
