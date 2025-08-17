-- previously known as internal_text_channel_convos

CREATE TABLE IF NOT EXISTS silver.internal_msg_convos (
    convo_id BIGINT NOT NULL,
    convo_summary TEXT,
    ingestion_timestamp TIMESTAMP
);

