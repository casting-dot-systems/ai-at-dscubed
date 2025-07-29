-- Create a table for storing Discord Channel history

CREATE TABLE IF NOT EXISTS bronze.discord_channels (
    server_id BIGINT NOT NULL,
    server_name VARCHAR(255) NOT NULL,
    channel_id BIGINT NOT NULL UNIQUE,
    channel_name VARCHAR(255) NOT NULL,
    channel_created_at TIMESTAMP NOT NULL,
    parent_id BIGINT,  -- Parent category ID, NULL for root channels
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add server columns if they don't exist (for existing tables)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'bronze' 
        AND table_name = 'discord_channels' 
        AND column_name = 'server_id'
    ) THEN
        ALTER TABLE bronze.discord_channels ADD COLUMN server_id BIGINT;
        ALTER TABLE bronze.discord_channels ADD COLUMN server_name VARCHAR(255);
    END IF;
END $$;

-- Add parent_id column if it doesn't exist (for existing tables)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'bronze' 
        AND table_name = 'discord_channels' 
        AND column_name = 'parent_id'
    ) THEN
        ALTER TABLE bronze.discord_channels ADD COLUMN parent_id BIGINT;
    END IF;
END $$;

-- Index for fast lookup by channel_id
CREATE INDEX IF NOT EXISTS idx_discord_channels_channel_id ON bronze.discord_channels(channel_id);
-- Index for parent_id lookups
CREATE INDEX IF NOT EXISTS idx_discord_channels_parent_id ON bronze.discord_channels(parent_id);
-- Index for server_id lookups
CREATE INDEX IF NOT EXISTS idx_discord_channels_server_id ON bronze.discord_channels(server_id);
