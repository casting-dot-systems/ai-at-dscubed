-- Table linking meetings to topics with topic summaries
CREATE TABLE IF NOT EXISTS silver.meeting_topics (
    meeting_id INTEGER REFERENCES silver.meeting(meeting_id) ON DELETE CASCADE,
    topic_id INTEGER REFERENCES silver.topic(topic_id) ON DELETE CASCADE,
    topic_summary TEXT,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (meeting_id, topic_id)
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_meeting_topics_meeting_id ON silver.meeting_topics(meeting_id);
CREATE INDEX IF NOT EXISTS idx_meeting_topics_topic_id ON silver.meeting_topics(topic_id);
