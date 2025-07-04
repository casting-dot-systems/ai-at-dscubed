-- Create a table for storing Notion Committee data
CREATE OR REPLACE TABLE bronze.committee (
    committee_id SERIAL PRIMARY KEY,
    name TEXT,
    notion_id TEXT,
    discord_id TEXT,
    discord_dm_channel_id BIGINT,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_committee_id ON bronze.committee(committee_id);
