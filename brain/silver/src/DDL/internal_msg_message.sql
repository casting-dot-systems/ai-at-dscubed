-- previously known as internal_text_channel_messages

CREATE TABLE IF NOT EXISTS silver.internal_msg_message (
    message_id SERIAL PRIMARY KEY,
    member_id INT,
    component_id BIGINT NOT NULL,
    msg_txt TEXT,
    msg_type TEXT,
    sent_at TIMESTAMP,
    edited_at TIMESTAMP,
    ingestion_timestamp TIMESTAMP
);

