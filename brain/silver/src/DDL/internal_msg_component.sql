-- previously known as internal_text_channel_meta

CREATE TABLE IF NOT EXISTS silver.internal_msg_component (
    component_id BIGINT NOT NULL UNIQUE,
    platform_name TEXT,
    component_type TEXT,
    parent_component_id BIGINT,
    component_name TEXT,
    created_at TIMESTAMP,
    archived_at TIMESTAMP,
    ingestion_timestamp TIMESTAMP
);

-- Add section_name column if it doesn't exist (for existing tables)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'silver' 
        AND table_name = 'internal_msg_component' 
        AND column_name = 'section_name'
    ) THEN
        ALTER TABLE silver.internal_msg_component ADD COLUMN section_name TEXT;
    END IF;
END $$;


