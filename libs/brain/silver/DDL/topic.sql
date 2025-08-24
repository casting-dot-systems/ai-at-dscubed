-- Table for storing unique topics extracted from meetings
CREATE TABLE IF NOT EXISTS silver.topic (
    topic_id SERIAL PRIMARY KEY,
    topic_name VARCHAR(255) NOT NULL UNIQUE,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for topic name lookups
CREATE INDEX IF NOT EXISTS idx_topic_name ON silver.topic(topic_name);
