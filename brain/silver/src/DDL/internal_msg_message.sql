-- previously known as internal_text_channel_messages

-- Create coerce function for member_id validation
CREATE OR REPLACE FUNCTION silver.coerce_member_id(input_member_id INT)
RETURNS INT AS $$
BEGIN
    -- If input is NULL or negative, return NULL for unknown
    IF input_member_id IS NULL OR input_member_id < 0 THEN
        RETURN NULL;
    END IF;
    
    -- If input is positive, check if it exists in committee table
    IF EXISTS (SELECT 1 FROM silver.committee WHERE member_id = input_member_id) THEN
        RETURN input_member_id;
    ELSE
        RETURN NULL; -- Return NULL for non-committee members
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE IF NOT EXISTS silver.internal_msg_message (
    message_id SERIAL PRIMARY KEY,
    member_id INT,
    component_id BIGINT NOT NULL,
    msg_txt TEXT,
    msg_type TEXT,
    sent_at TIMESTAMP,
    edited_at TIMESTAMP,
    ingestion_timestamp TIMESTAMP
);

