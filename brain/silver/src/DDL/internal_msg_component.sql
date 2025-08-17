-- previously known as internal_text_channel_meta

CREATE TABLE IF NOT EXISTS silver.internal_msg_component (
    component_id BIGINT NOT NULL PRIMARY KEY,
    platform_name TEXT,
    component_type TEXT,
    parent_component_id BIGINT,
    component_name TEXT,
    created_at TIMESTAMP,
    archived_at TIMESTAMP,
    ingestion_timestamp TIMESTAMP
);

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

-- Add primary key constraint if it doesn't exist (for existing tables)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE table_schema = 'silver' 
        AND table_name = 'internal_msg_component' 
        AND constraint_type = 'PRIMARY KEY'
    ) THEN
        ALTER TABLE silver.internal_msg_component ADD PRIMARY KEY (component_id);
    END IF;
END $$;

-- Convert parent_component_id to BIGINT if it's not already (for existing tables)
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'silver' 
        AND table_name = 'internal_msg_component' 
        AND column_name = 'parent_component_id'
        AND data_type != 'bigint'
    ) THEN
        ALTER TABLE silver.internal_msg_component 
        ALTER COLUMN parent_component_id TYPE BIGINT USING parent_component_id::BIGINT;
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


