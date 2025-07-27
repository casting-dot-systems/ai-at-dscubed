-- Table linking meetings to projects
CREATE TABLE silver.meeting_projects (
    meeting_id INTEGER REFERENCES silver.meeting(meeting_id) ON DELETE CASCADE,
    project_id INTEGER REFERENCES silver.project(project_id) ON DELETE CASCADE,
    PRIMARY KEY (meeting_id, project_id),
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
); 