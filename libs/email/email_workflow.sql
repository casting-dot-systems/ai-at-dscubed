DROP TABLE IF EXISTS email_workflow CASCADE;

CREATE TABLE IF NOT EXISTS email_workflow (
  id SERIAL PRIMARY KEY,
  thread_id VARCHAR(255) UNIQUE NOT NULL,
  step INTEGER NOT NULL DEFAULT 0,
  status VARCHAR(50) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_workflow_thread_id ON email_workflow(thread_id);