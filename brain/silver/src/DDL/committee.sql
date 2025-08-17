-- Silver layer table for storing committee data (will be loaded from bronze layer)
CREATE TABLE IF NOT EXISTS silver.committee (
    member_id SERIAL PRIMARY KEY,
    name TEXT,
    notion_id TEXT,
    discord_id BIGINT,
    discord_dm_channel_id BIGINT,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_committee_member_id ON silver.committee(member_id);

-- Insert unknown member record if it doesn't exist
INSERT INTO silver.committee (member_id, name, notion_id, discord_id, discord_dm_channel_id, ingestion_timestamp)
VALUES (-1, 'Unknown Member', NULL, NULL, NULL, CURRENT_TIMESTAMP)
ON CONFLICT (member_id) DO NOTHING;