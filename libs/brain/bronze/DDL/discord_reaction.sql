-- Create a table for storing Discord reaction data
CREATE TABLE IF NOT EXISTS bronze.discord_reactions (
    reaction_id VARCHAR(255) PRIMARY KEY,
    message_id BIGINT NOT NULL,
    reaction VARCHAR(100) NOT NULL,
    discord_username VARCHAR(255) NOT NULL,
    discord_user_id BIGINT NOT NULL,
    ingestion_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_discord_reaction_message_id ON bronze.discord_reaction(message_id);
CREATE INDEX IF NOT EXISTS idx_discord_reaction_user_id ON bronze.discord_reaction(discord_user_id);
