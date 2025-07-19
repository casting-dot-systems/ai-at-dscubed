-- Table linking committee members to projects
CREATE TABLE project_members (
    project_id INTEGER REFERENCES project(project_id) ON DELETE CASCADE,
    member_id INTEGER REFERENCES committee(member_id) ON DELETE CASCADE,
    PRIMARY KEY (project_id, member_id)
); 