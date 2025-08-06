
CREATE TABLE IF NOT EXISTS silver.internal_msg_members (
    member_id INT,
    component_id BIGINT,
    role TEXT,
    joined_at TIMESTAMP,
    left_at TIMESTAMP,   
    ingestion_timestamp TIMESTAMP
);

