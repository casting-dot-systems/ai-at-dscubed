-- DDL for internal_msg_convo_members table
CREATE TABLE IF NOT EXISTS silver.internal_msg_convo_members (
    convo_id INTEGER REFERENCES silver.internal_msg_convos(convo_id) ON DELETE CASCADE,
    member_id INTEGER REFERENCES silver.committee(member_id) ON DELETE CASCADE,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (convo_id, member_id)
);




