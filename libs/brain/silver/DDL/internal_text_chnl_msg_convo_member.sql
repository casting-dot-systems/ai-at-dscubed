-- Table linking individual messages to conversations and members
CREATE TABLE silver.internal_text_chnl_msg_convo_member (
    message_id BIGINT NOT NULL,
    member_id INTEGER REFERENCES silver.committee(member_id) ON DELETE CASCADE,
    convo_id INTEGER REFERENCES silver.internal_text_channel_convos(convo_id) ON DELETE CASCADE,
    PRIMARY KEY (message_id, convo_id),
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_internal_text_chnl_msg_convo_member_message_id ON silver.internal_text_chnl_msg_convo_member(message_id);
CREATE INDEX IF NOT EXISTS idx_internal_text_chnl_msg_convo_member_convo_id ON silver.internal_text_chnl_msg_convo_member(convo_id);
CREATE INDEX IF NOT EXISTS idx_internal_text_chnl_msg_convo_member_member_id ON silver.internal_text_chnl_msg_convo_member(member_id);