CREATE TABLE silver.llmgine_bus_events (
    event_id SERIAL PRIMARY KEY,
    event_data JSONB,
    event_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_class_name VARCHAR(255)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_llmgine_bus_events_event_timestamp 
ON silver.llmgine_bus_events(event_timestamp);

CREATE INDEX IF NOT EXISTS idx_llmgine_bus_events_class_name 
ON silver.llmgine_bus_events(event_class_name);