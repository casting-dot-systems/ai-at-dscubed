DROP TABLE IF EXISTS emails CASCADE;
DROP TYPE IF EXISTS sender_type;

CREATE TYPE sender_type AS ENUM ('user', 'agent');

CREATE TABLE emails (
    thread_id TEXT NOT NULL,
    email_id TEXT NOT NULL,
    user_email TEXT NOT NULL,
    sender sender_type NOT NULL,
    body TEXT NOT NULL,
    subject TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (email_id),
    CONSTRAINT fk_emails_user_email
        FOREIGN KEY (user_email)
        REFERENCES email_users(email)
        ON DELETE CASCADE
);

COMMENT ON TABLE emails IS 'Stores individual email messages for the Gmail agent.';


CREATE INDEX IF NOT EXISTS idx_emails_thread_id ON emails(thread_id);
CREATE INDEX IF NOT EXISTS idx_emails_user_email ON emails(user_email);
CREATE INDEX IF NOT EXISTS idx_emails_timestamp ON emails(timestamp);