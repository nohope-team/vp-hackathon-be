CREATE TABLE n8n_executions (
    id INTEGER PRIMARY KEY,
    workflow_id VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    execution_data JSONB,
    processed BOOLEAN DEFAULT FALSE,
    langfuse_trace_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);