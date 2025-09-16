-- Create a table for storing Discord reaction data
CREATE TABLE IF NOT EXISTS bronze.discord_reactions (
    reaction_id SERIAL PRIMARY KEY,
    message_id TEXT NOT NULL,
    reaction TEXT NOT NULL,
    discord_username TEXT NOT NULL,
    discord_user_id TEXT NOT NULL,
    ingestion_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraint to link to discord_chats
    CONSTRAINT fk_discord_reactions_message_id 
        FOREIGN KEY (message_id) 
        REFERENCES bronze.discord_chats(message_id) 
        ON DELETE CASCADE
);

-- Create indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_discord_reactions_message_id ON bronze.discord_reactions(message_id);
CREATE INDEX IF NOT EXISTS idx_discord_reactions_user_id ON bronze.discord_reactions(discord_user_id);

