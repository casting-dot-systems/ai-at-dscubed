
-- table for storing discord relevant channels (defined by us)
CREATE TABLE IF NOT EXISTS bronze.discord_relevant_channels (
    server_id BIGINT NOT NULL,
    server_name VARCHAR(255) NOT NULL,
    channel_id BIGINT NOT NULL,
    channel_name VARCHAR(255) NOT NULL,
    ingest BOOLEAN DEFAULT TRUE,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- composite Primary Key
    PRIMARY KEY (server_id, channel_id)
);



