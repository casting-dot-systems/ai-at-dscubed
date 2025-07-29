-- Create a table for storing Discord Channel history

CREATE TABLE IF NOT EXISTS bronze.discord_channels (
    server_id BIGINT NOT NULL,
    server_name VARCHAR(255) NOT NULL,
    channel_id BIGINT NOT NULL UNIQUE,
    channel_name VARCHAR(255) NOT NULL,
    channel_created_at TIMESTAMP NOT NULL,
    parent_id BIGINT,  -- Parent category ID, NULL for root channels
    entity_type VARCHAR(50),  -- Discord entity type (discord_channel, discord_thread, discord_server, discord_forum)
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

-- Add entity_type column if it doesn't exist (for existing tables)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'bronze' 
        AND table_name = 'discord_channels' 
        AND column_name = 'entity_type'
    ) THEN
        ALTER TABLE bronze.discord_channels ADD COLUMN entity_type VARCHAR(50);
    END IF;
END $$;
