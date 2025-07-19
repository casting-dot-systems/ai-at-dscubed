-- Table linking meetings to projects
CREATE TABLE meeting_projects (
    meeting_id INTEGER REFERENCES meeting(meeting_id) ON DELETE CASCADE,
    project_id INTEGER REFERENCES project(project_id) ON DELETE CASCADE,
    PRIMARY KEY (meeting_id, project_id)
); 