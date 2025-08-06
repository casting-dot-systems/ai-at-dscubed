
-- table for storing discord relevant channels (defined by us)
CREATE TABLE IF NOT EXISTS bronze.discord_relevant_channels (
    server_id BIGINT NOT NULL,
    server_name VARCHAR(255) NOT NULL,
    channel_id BIGINT NOT NULL,
    channel_name VARCHAR(255) NOT NULL,
    channel_created_at TIMESTAMP,
    parent_id BIGINT,  -- Parent category ID, NULL for root channels
    section_name VARCHAR(255),  -- Name of the section/category the channel belongs to
    entity_type VARCHAR(50),  -- Discord entity type (discord_channel, discord_thread, discord_section, discord_forum)
    ingest BOOLEAN DEFAULT TRUE,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- composite Primary Key
    PRIMARY KEY (server_id, channel_id)
);

-- Add parent_id column if it doesn't exist (for existing tables)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'bronze' 
        AND table_name = 'discord_relevant_channels' 
        AND column_name = 'parent_id'
    ) THEN
        ALTER TABLE bronze.discord_relevant_channels ADD COLUMN parent_id BIGINT;
    END IF;
END $$;

-- Add section_name column if it doesn't exist (for existing tables)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'bronze' 
        AND table_name = 'discord_relevant_channels' 
        AND column_name = 'section_name'
    ) THEN
        ALTER TABLE bronze.discord_relevant_channels ADD COLUMN section_name VARCHAR(255);
    END IF;
END $$;

-- Add entity_type column if it doesn't exist (for existing tables)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'bronze' 
        AND table_name = 'discord_relevant_channels' 
        AND column_name = 'entity_type'
    ) THEN
        ALTER TABLE bronze.discord_relevant_channels ADD COLUMN entity_type VARCHAR(50);
    END IF;
END $$;



