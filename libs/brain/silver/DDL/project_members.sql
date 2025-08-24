-- Table linking committee members to projects
CREATE TABLE silver.project_members (
    project_id INTEGER REFERENCES silver.project(project_id) ON DELETE CASCADE,
    member_id INTEGER REFERENCES silver.committee(member_id) ON DELETE CASCADE,
    PRIMARY KEY (project_id, member_id),
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
); 