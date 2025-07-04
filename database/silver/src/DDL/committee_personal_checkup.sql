-- Create a table (SCD2) for storing scrum checkup history of committee members
CREATE TABLE IF NOT EXISTS silver.committee_personal_checkup (
    checkup_id SERIAL PRIMARY KEY,
    member_id BIGINT NOT NULL REFERENCES bronze.committee(member_id),
    committee_name TEXT,
    personal_description TEXT,
    checkup_text TEXT,
    start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_date TIMESTAMP DEFAULT '9999-12-31',
    is_current BOOLEAN DEFAULT TRUE,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

CREATE INDEX IF NOT EXISTS idx_committee_personal_checkup_checkup_id ON silver.committee_personal_checkup(checkup_id);
CREATE INDEX IF NOT EXISTS idx_committee_personal_checkup_member_id ON silver.committee_personal_checkup(member_id);