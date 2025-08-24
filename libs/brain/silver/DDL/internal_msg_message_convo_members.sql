-- DDL for internal_msg_message_convo_members table
CREATE TABLE IF NOT EXISTS silver.internal_msg_message_convo_members (
    message_id BIGINT PRIMARY KEY,
    member_id INTEGER REFERENCES silver.committee(member_id) ON DELETE CASCADE,
    convo_id INTEGER REFERENCES silver.internal_msg_convos(convo_id) ON DELETE CASCADE,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(message_id, convo_id)
);




