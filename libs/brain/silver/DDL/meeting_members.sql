-- Table linking committee members to meetings
CREATE TABLE silver.meeting_members (
    meeting_id INTEGER REFERENCES silver.meeting(meeting_id) ON DELETE CASCADE,
    member_id INTEGER REFERENCES silver.committee(member_id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    PRIMARY KEY (meeting_id, member_id),
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
); 