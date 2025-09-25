create or replace function catalog.touch_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end$$;

drop trigger if exists trg_members_touch on catalog.members;
create trigger trg_members_touch
before update on catalog.members
for each row
execute function catalog.touch_updated_at();
