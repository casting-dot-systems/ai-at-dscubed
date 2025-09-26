-- Auto-update updated_at_ts
CREATE OR REPLACE FUNCTION SILVER.TOUCH_MESSAGE_REACTIONS_UPDATED_AT () RETURNS TRIGGER LANGUAGE PLPGSQL AS $$
begin
  new.updated_at_ts := now();
  return new;
end$$;