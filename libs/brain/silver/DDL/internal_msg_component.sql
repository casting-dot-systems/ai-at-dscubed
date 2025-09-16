-- previously known as internal_text_channel_meta

CREATE TABLE IF NOT EXISTS silver.internal_msg_component (
    component_id SERIAL PRIMARY KEY,
    src_component_id TEXT NOT NULL,
    component_type TEXT,
    parent_component_id INT,
    component_name TEXT,
    created_at TIMESTAMP,
    archived_at TIMESTAMP,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add src_component_id column if it doesn't exist (for existing tables)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'silver' 
        AND table_name = 'internal_msg_component' 
        AND column_name = 'src_component_id'
    ) THEN
        ALTER TABLE silver.internal_msg_component ADD COLUMN src_component_id VARCHAR(255);
    END IF;
END $$;

-- Drop section_name column if it exists (for existing tables)
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'silver' 
        AND table_name = 'internal_msg_component' 
        AND column_name = 'section_name'
    ) THEN
        ALTER TABLE silver.internal_msg_component DROP COLUMN section_name;
    END IF;
END $$;

-- Convert component_id to SERIAL if it's not already (for existing tables)
DO $$ 
BEGIN
    -- This is complex for existing tables, so we'll handle it in the migration script
    -- For now, just ensure it's an integer type
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'silver' 
        AND table_name = 'internal_msg_component' 
        AND column_name = 'component_id'
        AND data_type NOT IN ('integer', 'bigint')
    ) THEN
        ALTER TABLE silver.internal_msg_component 
        ALTER COLUMN component_id TYPE INTEGER;
    END IF;
END $$;

-- Convert parent_component_id to INT if it's not already (for existing tables)
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'silver' 
        AND table_name = 'internal_msg_component' 
        AND column_name = 'parent_component_id'
        AND data_type NOT IN ('integer', 'int4')
    ) THEN
        ALTER TABLE silver.internal_msg_component 
        ALTER COLUMN parent_component_id TYPE INTEGER USING parent_component_id::INTEGER;
    END IF;
END $$;

-- Clean up orphaned parent_component_id references before adding foreign key constraint
DO $$ 
BEGIN
    -- Set parent_component_id to NULL where it references non-existent component_id
    UPDATE silver.internal_msg_component 
    SET parent_component_id = NULL 
    WHERE parent_component_id IS NOT NULL 
    AND parent_component_id NOT IN (
        SELECT component_id FROM silver.internal_msg_component
    );
END $$;

-- Add self-referential foreign key constraint if it doesn't exist (for existing tables)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE table_schema = 'silver' 
        AND table_name = 'internal_msg_component' 
        AND constraint_name = 'internal_msg_component_parent_fk'
    ) THEN
        ALTER TABLE silver.internal_msg_component 
        ADD CONSTRAINT internal_msg_component_parent_fk 
        FOREIGN KEY (parent_component_id) REFERENCES silver.internal_msg_component(component_id);
    END IF;
END $$;

-- Add foreign key constraint to link to source component in bronze layer
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE table_schema = 'silver' 
        AND table_name = 'internal_msg_component' 
        AND constraint_name = 'fk_internal_msg_component_src_component_id'
    ) THEN
        ALTER TABLE silver.internal_msg_component 
        ADD CONSTRAINT fk_internal_msg_component_src_component_id 
        FOREIGN KEY (src_component_id) REFERENCES bronze.discord_channels(channel_id) 
        ON DELETE CASCADE;
    END IF;
END $$;

-- Indexes for common query patterns

-- Index for filtering by component_type (channels, categories, etc.)
CREATE INDEX IF NOT EXISTS idx_internal_msg_component_component_type 
    ON silver.internal_msg_component(component_type);

-- Index for hierarchical queries (finding child components by parent)
CREATE INDEX IF NOT EXISTS idx_internal_msg_component_parent_component_id 
    ON silver.internal_msg_component(parent_component_id);

-- Index for name-based searches and filtering
CREATE INDEX IF NOT EXISTS idx_internal_msg_component_component_name 
    ON silver.internal_msg_component(component_name);

-- Index for source component ID lookups (deduplication, cross-referencing)
CREATE INDEX IF NOT EXISTS idx_internal_msg_component_src_component_id 
    ON silver.internal_msg_component(src_component_id);

-- Index for time-based queries (filtering by creation date)
CREATE INDEX IF NOT EXISTS idx_internal_msg_component_created_at 
    ON silver.internal_msg_component(created_at);

-- Index for archived components (filtering by archive date)
CREATE INDEX IF NOT EXISTS idx_internal_msg_component_archived_at 
    ON silver.internal_msg_component(archived_at) 
    WHERE archived_at IS NOT NULL;

-- Index for ingestion timestamp (data pipeline monitoring)
CREATE INDEX IF NOT EXISTS idx_internal_msg_component_ingestion_timestamp 
    ON silver.internal_msg_component(ingestion_timestamp);

-- Composite index for type + parent queries (finding components of specific type under a parent)
CREATE INDEX IF NOT EXISTS idx_internal_msg_component_type_parent 
    ON silver.internal_msg_component(component_type, parent_component_id);

-- Composite index for parent + name queries (finding child components by name under a parent)
CREATE INDEX IF NOT EXISTS idx_internal_msg_component_parent_name 
    ON silver.internal_msg_component(parent_component_id, component_name);

-- Composite index for type + created_at (finding components of specific type created in time range)
CREATE INDEX IF NOT EXISTS idx_internal_msg_component_type_created_at 
    ON silver.internal_msg_component(component_type, created_at);

-- Index for active components (not archived)
CREATE INDEX IF NOT EXISTS idx_internal_msg_component_active 
    ON silver.internal_msg_component(component_id) 
    WHERE archived_at IS NULL;




