-- Create a table for storing Discord chat history
CREATE TABLE IF NOT EXISTS bronze.discord_chats (
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
CREATE INDEX IF NOT EXISTS idx_discord_chats_channel_id ON bronze.discord_chats(channel_id);
CREATE INDEX IF NOT EXISTS idx_discord_chats_thread_id ON bronze.discord_chats(thread_id);
CREATE INDEX IF NOT EXISTS idx_discord_chats_user_id ON bronze.discord_chats(discord_user_id);
CREATE INDEX IF NOT EXISTS idx_discord_chats_chat_created_at ON bronze.discord_chats(chat_created_at);

-- Add a unique constraint to prevent duplicate messages
CREATE UNIQUE INDEX IF NOT EXISTS idx_discord_chats_unique_message 
ON bronze.discord_chats(channel_id, message_id, thread_id) 
WHERE thread_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_discord_chats_unique_channel_message 
ON bronze.discord_chats(channel_id, message_id) 
WHERE thread_id IS NULL; 