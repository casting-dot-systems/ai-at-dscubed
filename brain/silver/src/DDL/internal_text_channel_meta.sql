
CREATE TABLE IF NOT EXISTS silver.internal_text_channel_meta (
    channel_id BIGINT NOT NULL UNIQUE,
    source_name TEXT,
    channel_type TEXT,
    channel_name TEXT,
    description TEXT,
    parent_id BIGINT,
    section_name TEXT,  -- Name of the section/category the channel belongs to
    date_created TIMESTAMP
);

-- Add section_name column if it doesn't exist (for existing tables)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'silver' 
        AND table_name = 'internal_text_channel_meta' 
        AND column_name = 'section_name'
    ) THEN
        ALTER TABLE silver.internal_text_channel_meta ADD COLUMN section_name TEXT;
    END IF;
END $$;

