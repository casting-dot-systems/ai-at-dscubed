-- Table for committee members
CREATE TABLE committee (
    member_id SERIAL PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    join_date DATE NOT NULL,
    committee_role VARCHAR(100),
    status VARCHAR(20)
); 