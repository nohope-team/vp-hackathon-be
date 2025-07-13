CREATE TABLE n8n_flows (
    id SERIAL PRIMARY KEY,
    flow_id VARCHAR(100) UNIQUE NOT NULL,
    flow_name VARCHAR(255),
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);