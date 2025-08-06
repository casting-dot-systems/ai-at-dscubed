-- previously known as internal_text_channel_convo_members

CREATE TABLE IF NOT EXISTS silver.internal_msg_component_convo_members (
    convo_id BIGINT NOT NULL,
    member_id BIGINT NOT NULL,
    ingestion_timestamp TIMESTAMP
);

