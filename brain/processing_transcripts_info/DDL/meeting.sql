-- Table for meetings
CREATE TABLE meeting (
    meeting_id SERIAL PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    transcript_link TEXT,
    date TIMESTAMP NOT NULL,
    meeting_summary TEXT
); 