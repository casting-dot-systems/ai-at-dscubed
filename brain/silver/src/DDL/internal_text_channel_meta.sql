
CREATE TABLE IF NOT EXISTS silver.internal_text_channel_meta (
    channel_id BIGINT NOT NULL UNIQUE,
    source_name TEXT,
    channel_type TEXT,
    channel_name TEXT,
    description TEXT,
    parent_id BIGINT,
    date_created TIMESTAMP
);