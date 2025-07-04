-- Create a table for storing Discord chat history
CREATE TABLE IF NOT EXISTS bronze.discord_chat (
    chat_id SERIAL PRIMARY KEY,
    channel_id BIGINT NOT NULL,
    channel_name VARCHAR(255) NOT NULL,
    thread_name VARCHAR(255),
    thread_id BIGINT,
    message_id BIGINT NOT NULL,
    discord_username VARCHAR(255) NOT NULL,
    discord_user_id BIGINT NOT NULL,
    content TEXT,
    chat_created_at TIMESTAMP NOT NULL,
    chat_edited_at TIMESTAMP,
    is_thread BOOLEAN NOT NULL DEFAULT FALSE,
    ingestion_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_discord_chat_channel_id ON bronze.discord_chat_table(channel_id);
CREATE INDEX IF NOT EXISTS idx_discord_chat_thread_id ON bronze.discord_chat_table(thread_id);
CREATE INDEX IF NOT EXISTS idx_discord_chat_author_id ON bronze.discord_chat_table(author_id);
CREATE INDEX IF NOT EXISTS idx_discord_chat_chat_created_at ON bronze.discord_chat_table(chat_created_at);

-- Add a unique constraint to prevent duplicate messages
CREATE UNIQUE INDEX IF NOT EXISTS idx_discord_chat_unique_message 
ON bronze.discord_chat_table(channel_id, message_id, thread_id) 
WHERE thread_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_discord_chat_unique_channel_message 
ON bronze.discord_chat_table(channel_id, message_id) 
WHERE thread_id IS NULL; 