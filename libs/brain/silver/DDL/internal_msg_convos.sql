<<<<<<< HEAD:brain/silver/src/DDL/internal_msg_convos.sql
-- previously known as internal_text_channel_convos

CREATE TABLE IF NOT EXISTS silver.internal_msg_convos (
    convo_id BIGINT NOT NULL,
    convo_summary TEXT,
    ingestion_timestamp TIMESTAMP
);

=======
-- DDL for internal_msg_convos table
CREATE TABLE IF NOT EXISTS silver.internal_msg_convos (
    convo_id SERIAL PRIMARY KEY,
    convo_summary TEXT,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);




>>>>>>> f/brain:libs/brain/silver/DDL/internal_msg_convos.sql
