
CREATE TABLE IF NOT EXISTS silver.internal_text_channel_messages (
    message_id BIGINT NOT NULL UNIQUE,
    member_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    message TEXT,
    date_created TIMESTAMP
);

