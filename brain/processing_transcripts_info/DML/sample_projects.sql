-- Sample data for projects
INSERT INTO projects (name, description) VALUES
('Even''s Marathon', 'Organizing a charity marathon event led by Even.'),
('Nathan''s Web', 'Developing a personal website and blog for Nathan.'),
('PJ''s Database', 'Designing and implementing a database system for PJ''s research project.');

-- Sample data for people
INSERT INTO people (name) VALUES
('Alex Carter'),
('John Smith'),
('Ryan Smith'),
('Olivia Brown'),
('Lucas Miller');

-- Sample data for project members
-- Even's Marathon: Alex, Olivia
INSERT INTO project_members (project_id, person_id) VALUES (1, 1), (1, 4);
-- Nathan's Web: Megan, Lucas
INSERT INTO project_members (project_id, person_id) VALUES (2, 2), (2, 5);
-- PJ's Database: Ryan, Megan, Olivia
INSERT INTO project_members (project_id, person_id) VALUES (3, 3), (3, 2), (3, 4);
