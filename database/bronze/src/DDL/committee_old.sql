CREATE TABLE IF NOT EXISTS bronze.committee_old (
    committee_id         SERIAL PRIMARY KEY,
    name                 TEXT,
    role                 TEXT,
    status               TEXT,
    team                 TEXT,
    joined               TEXT,
    bio                  TEXT,
    email                TEXT,
    discord_tag          TEXT,
    facebook             TEXT,
    instagram            TEXT,
    linkedin             TEXT,
    working_on           TEXT,
    workload             TEXT,
    last_edited_time     TIMESTAMP,                 
    ingestion_timestamp  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX IF NOT EXISTS idx_committee_name                ON bronze.committee(name);
CREATE INDEX IF NOT EXISTS idx_committee_status              ON bronze.committee(status);
CREATE INDEX IF NOT EXISTS idx_committee_team                ON bronze.committee(team);
CREATE INDEX IF NOT EXISTS idx_committee_last_edited_time    ON bronze.committee(last_edited_time);
CREATE INDEX IF NOT EXISTS idx_committee_ingestion_timestamp ON bronze.committee(ingestion_timestamp);
