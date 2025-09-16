-- DDL for internal_msg_reactions table
-- This table stores reaction data from the silver layer, linked to messages in internal_msg_message

CREATE TABLE IF NOT EXISTS silver.internal_msg_reactions (
    reaction_id SERIAL PRIMARY KEY,
    message_id INT NOT NULL,
    src_message_id TEXT NOT NULL,
    reaction TEXT NOT NULL,
    member_id INT,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraint to link to internal_msg_message
    CONSTRAINT fk_internal_msg_reactions_message_id 
        FOREIGN KEY (message_id) 
        REFERENCES silver.internal_msg_message(message_id) 
        ON DELETE CASCADE,
    
    -- Foreign key constraint to link to committee
    CONSTRAINT fk_internal_msg_reactions_member_id 
        FOREIGN KEY (member_id) 
        REFERENCES silver.committee(member_id) 
        ON DELETE CASCADE,
    
    -- Foreign key constraint to link to source message in bronze layer
    CONSTRAINT fk_internal_msg_reactions_src_message_id 
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
        AND table_name = 'internal_msg_reactions' 
        AND column_name = 'member_id'
        AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE silver.internal_msg_reactions ALTER COLUMN member_id DROP NOT NULL;
        RAISE NOTICE 'Dropped NOT NULL constraint from member_id column in reactions table';
    END IF;
END $$;

-- Create indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_internal_msg_reactions_src_message_id 
    ON silver.internal_msg_reactions(src_message_id);
    
    
CREATE INDEX IF NOT EXISTS idx_internal_msg_reactions_member_id 
    ON silver.internal_msg_reactions(member_id);
    
CREATE INDEX IF NOT EXISTS idx_internal_msg_reactions_reaction 
    ON silver.internal_msg_reactions(reaction);

-- Index for message_id (primary foreign key - very important for JOINs)
CREATE INDEX IF NOT EXISTS idx_internal_msg_reactions_message_id 
    ON silver.internal_msg_reactions(message_id);

-- Index for ingestion timestamp (data pipeline monitoring)
CREATE INDEX IF NOT EXISTS idx_internal_msg_reactions_ingestion_timestamp 
    ON silver.internal_msg_reactions(ingestion_timestamp);

-- Composite index for message + reaction queries (finding all reactions on a specific message)
CREATE INDEX IF NOT EXISTS idx_internal_msg_reactions_message_reaction 
    ON silver.internal_msg_reactions(message_id, reaction);

-- Composite index for member + reaction queries (finding all reactions by a member of a specific type)
CREATE INDEX IF NOT EXISTS idx_internal_msg_reactions_member_reaction 
    ON silver.internal_msg_reactions(member_id, reaction);

-- Composite index for message + member queries (finding reactions by a specific member on a specific message)
CREATE INDEX IF NOT EXISTS idx_internal_msg_reactions_message_member 
    ON silver.internal_msg_reactions(message_id, member_id);

