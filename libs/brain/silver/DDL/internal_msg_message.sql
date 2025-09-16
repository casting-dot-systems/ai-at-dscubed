-- DDL for internal_msg_message table
CREATE TABLE IF NOT EXISTS silver.internal_msg_message (
    message_id SERIAL PRIMARY KEY,
    src_message_id TEXT NOT NULL,
    member_id INT,
    component_id INT NOT NULL,
    message_txt TEXT,
    message_type TEXT,
    sent_at TIMESTAMP,
    edited_at TIMESTAMP,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraint to link to internal_msg_component
    CONSTRAINT fk_internal_msg_message_component_id 
        FOREIGN KEY (component_id) 
        REFERENCES silver.internal_msg_component(component_id) 
        ON DELETE CASCADE,
    
    -- Foreign key constraint to link to committee (only for committee members)
    CONSTRAINT fk_internal_msg_message_member_id 
        FOREIGN KEY (member_id) 
        REFERENCES silver.committee(member_id) 
        ON DELETE CASCADE,
    
    -- Foreign key constraint to link to source message in bronze layer
    CONSTRAINT fk_internal_msg_message_src_message_id 
        FOREIGN KEY (src_message_id) 
        REFERENCES bronze.discord_chats(message_id) 
        ON DELETE CASCADE
);

-- Migration: Drop NOT NULL constraint from member_id if it exists (for existing tables)
DO $$ 
BEGIN
    -- Check if member_id column has NOT NULL constraint and drop it
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'silver' 
        AND table_name = 'internal_msg_message' 
        AND column_name = 'member_id'
        AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE silver.internal_msg_message ALTER COLUMN member_id DROP NOT NULL;
        RAISE NOTICE 'Dropped NOT NULL constraint from member_id column';
    END IF;
END $$;

-- Indexes for common query patterns

-- Index for filtering by component_id (most common query pattern)
CREATE INDEX IF NOT EXISTS idx_internal_msg_message_component_id 
    ON silver.internal_msg_message(component_id);

-- Index for filtering by member_id (finding messages from specific members)
CREATE INDEX IF NOT EXISTS idx_internal_msg_message_member_id 
    ON silver.internal_msg_message(member_id);

-- Index for time-based queries (filtering by sent_at timestamp)
CREATE INDEX IF NOT EXISTS idx_internal_msg_message_sent_at 
    ON silver.internal_msg_message(sent_at);

-- Index for message type filtering
CREATE INDEX IF NOT EXISTS idx_internal_msg_message_message_type 
    ON silver.internal_msg_message(message_type);

-- Composite index for component + time range queries (very common pattern)
CREATE INDEX IF NOT EXISTS idx_internal_msg_message_component_sent_at 
    ON silver.internal_msg_message(component_id, sent_at);

-- Composite index for member + time range queries
CREATE INDEX IF NOT EXISTS idx_internal_msg_message_member_sent_at 
    ON silver.internal_msg_message(member_id, sent_at);

-- Index for ingestion timestamp (useful for data pipeline monitoring)
CREATE INDEX IF NOT EXISTS idx_internal_msg_message_ingestion_timestamp 
    ON silver.internal_msg_message(ingestion_timestamp);

-- Composite index for component + member queries (finding messages from specific member in specific component)
CREATE INDEX IF NOT EXISTS idx_internal_msg_message_component_member 
    ON silver.internal_msg_message(component_id, member_id);

-- Index for edited messages (filtering by edited_at)
CREATE INDEX IF NOT EXISTS idx_internal_msg_message_edited_at 
    ON silver.internal_msg_message(edited_at) 
    WHERE edited_at IS NOT NULL;

-- Index for source message ID (foreign key to bronze.discord_chats)
CREATE INDEX IF NOT EXISTS idx_internal_msg_message_src_message_id 
    ON silver.internal_msg_message(src_message_id);




