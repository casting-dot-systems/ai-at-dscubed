-- table for storing discord relevant channels (defined by us)
CREATE TABLE IF NOT EXISTS bronze.discord_relevant_channels (
    server_id TEXT,
    server_name TEXT,
    channel_id TEXT NOT NULL,
    channel_name TEXT,
    channel_created_at TIMESTAMP NOT NULL,
    parent_id TEXT,  -- Parent category ID, NULL for root channels
    section_name TEXT,  -- Name of the section/category the channel belongs to
    entity_type TEXT,  -- Discord entity type (discord_channel, discord_thread, discord_section, discord_forum)
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- composite Primary Key
    PRIMARY KEY (server_id, channel_id)
);

-- (Optional) Only needed when migrating an older table that might not have these columns:
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'bronze' 
          AND table_name = 'discord_relevant_channels' 
          AND column_name = 'parent_id'
    ) THEN
        ALTER TABLE bronze.discord_relevant_channels ADD COLUMN parent_id TEXT;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'bronze' 
          AND table_name = 'discord_relevant_channels' 
          AND column_name = 'section_name'
    ) THEN
        ALTER TABLE bronze.discord_relevant_channels ADD COLUMN section_name TEXT;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'bronze' 
          AND table_name = 'discord_relevant_channels' 
          AND column_name = 'entity_type'
    ) THEN
        ALTER TABLE bronze.discord_relevant_channels ADD COLUMN entity_type TEXT;
    END IF;
END $$;

-- Convert parent_id to TEXT if it's not already (for existing tables)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'bronze' 
          AND table_name = 'discord_relevant_channels' 
          AND column_name = 'parent_id'
          AND data_type <> 'text'
    ) THEN
        ALTER TABLE bronze.discord_relevant_channels 
        ALTER COLUMN parent_id TYPE TEXT USING parent_id::TEXT;
    END IF;
END $$;
