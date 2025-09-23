DROP TABLE IF EXISTS email_users CASCADE;

CREATE TABLE email_users (
    users_email_id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    name TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_email_users_email UNIQUE (email)
);

COMMENT ON TABLE email_users IS 'Stores user information for the Gmail agent.';




