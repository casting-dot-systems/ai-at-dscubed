-- Create a table for storing Discord Channel history

CREATE TABLE IF NOT EXISTS bronze.discord_channel (
    channel_id BIGINT NOT NULL UNIQUE,
    channel_name VARCHAR(255) NOT NULL,
    channel_created_at TIMESTAMP NOT NULL,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast lookup by channel_id
CREATE INDEX IF NOT EXISTS idx_discord_channel_channel_id ON bronze.discord_channel(channel_id);
