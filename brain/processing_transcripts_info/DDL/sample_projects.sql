-- Table for projects
CREATE TABLE projects (
    project_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT
);

-- Table for people
CREATE TABLE people (
    person_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

-- Table linking people to projects
CREATE TABLE project_members (
    project_id INTEGER REFERENCES projects(project_id),
    person_id INTEGER REFERENCES people(person_id),
    PRIMARY KEY (project_id, person_id)
);
