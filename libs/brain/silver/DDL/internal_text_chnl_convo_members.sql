-- Table linking committee members to internal text channel conversations
CREATE TABLE silver.internal_text_chnl_convo_members (
    convo_id INTEGER REFERENCES silver.internal_text_channel_convos(convo_id) ON DELETE CASCADE,
    member_id INTEGER REFERENCES silver.committee(member_id) ON DELETE CASCADE,
    PRIMARY KEY (convo_id, member_id),
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_internal_text_chnl_convo_members_convo_id ON silver.internal_text_chnl_convo_members(convo_id);
CREATE INDEX IF NOT EXISTS idx_internal_text_chnl_convo_members_member_id ON silver.internal_text_chnl_convo_members(member_id); 