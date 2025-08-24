-- DDL for internal_msg_convos table
CREATE TABLE IF NOT EXISTS silver.internal_msg_convos (
    convo_id SERIAL PRIMARY KEY,
    convo_summary TEXT,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);




