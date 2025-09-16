-- Create a table for storing Discord Channel history

CREATE TABLE IF NOT EXISTS bronze.discord_channels (
    server_id TEXT,
    server_name TEXT,
    channel_id TEXT PRIMARY KEY NOT NULL,
    channel_name TEXT,
    channel_created_at TIMESTAMP NOT NULL,
    parent_id TEXT,  -- Parent category ID, NULL for root channels
    section_name TEXT,  -- Name of the section/category the channel belongs to
    entity_type TEXT,  -- Discord entity type (discord_channel, discord_thread, discord_section, discord_forum)
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
        ALTER TABLE bronze.discord_channels ADD COLUMN server_id TEXT;
        ALTER TABLE bronze.discord_channels ADD COLUMN server_name TEXT;
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
        ALTER TABLE bronze.discord_channels ADD COLUMN parent_id TEXT;
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
        ALTER TABLE bronze.discord_channels ADD COLUMN entity_type TEXT;
    END IF;
END $$;

-- Add section_name column if it doesn't exist (for existing tables)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'bronze' 
        AND table_name = 'discord_channels' 
        AND column_name = 'section_name'
    ) THEN
        ALTER TABLE bronze.discord_channels ADD COLUMN section_name TEXT;
    END IF;
END $$;
