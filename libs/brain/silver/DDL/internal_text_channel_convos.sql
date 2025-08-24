-- Table for storing internal text channel conversations
CREATE TABLE silver.internal_text_channel_convos (
    convo_id SERIAL PRIMARY KEY,
    convo_summary TEXT,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);