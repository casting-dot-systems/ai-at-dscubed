-- Create coerce function for member_id validation
CREATE OR REPLACE FUNCTION silver.coerce_member_id(input_member_id INT)
RETURNS INT AS $$
BEGIN
    -- If input is NULL or negative, return -1 for unknown
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

CREATE TABLE IF NOT EXISTS silver.internal_msg_message_convo_members (
    message_id BIGINT NOT NULL,
    member_id INT,
    convo_id BIGINT NOT NULL,
    ingestion_timestamp TIMESTAMP
);

