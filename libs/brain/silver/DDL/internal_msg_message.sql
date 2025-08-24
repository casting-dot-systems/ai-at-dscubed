-- DDL for internal_msg_message table
CREATE TABLE IF NOT EXISTS silver.internal_msg_message (
    message_id BIGINT PRIMARY KEY,
    member_id BIGINT,
    component_id BIGINT,
    msg_txt TEXT,
    sent_at TIMESTAMP,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);




