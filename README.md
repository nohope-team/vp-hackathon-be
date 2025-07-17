# Multi-Agent Platform Backend

FastAPI backend system for a multi-agent platform using Amazon Bedrock Architecture and n8n workflow integration with Langfuse observability.

## Architecture

```
API Gateway → FastAPI → Step Functions (SuperAgent) → Bedrock Agents (SubAgents)
                    ↓
            SQS/SNS → Lambda (Tools/Plugins)
                    ↓
            PostgreSQL (State) + Langfuse (Observability) + CloudWatch (Monitoring)
```

## Features

- ✅ REST API endpoint `/chat` for client requests
- ✅ Step Functions integration for SuperAgent orchestration
- ✅ Amazon Bedrock integration for SubAgents management
- ✅ SQS/SNS support for Lambda function integration
- ✅ n8n workflow execution tracking and monitoring
- ✅ Langfuse integration for AI observability and cost tracking
- ✅ Facebook Messenger webhook integration
- ✅ Structured JSON logging
- ✅ Docker containerization
- ✅ Swagger UI/ReDoc documentation

## Local Setup

### Requirements
- Python 3.10+
- Docker & Docker Compose
- PostgreSQL database
- n8n instance (optional)
- Langfuse account (optional)

### Step 1: Clone and setup
```bash
git clone <repository>
cd VPHackathon/be
```

### Step 2: Configure environment
```bash
# Copy and edit .env file
cp .env.example .env
# Update AWS credentials, database URL, and API keys
```

### Step 3: Install dependencies
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install packages
pip install -r requirements.txt
```

### Step 4: Run the application

#### Option 1: Run directly
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Option 2: Using Docker
```bash
# Build and run
docker-compose up --build
```

## API Usage

### Facebook Workflow Endpoints

#### Get Workflows
```bash
curl -X GET "http://localhost:8000/api/v1/facebook-workflow?limit=10&offset=0"
```

#### Get Workflow by ID
```bash
curl -X GET "http://localhost:8000/api/v1/facebook-workflow/1"
```

#### Create Workflow
```bash
curl -X POST "http://localhost:8000/api/v1/facebook-workflow/" \
  -H "Content-Type: application/json" \
  -d '{
    "user_question": "How to reset my password?",
    "chatbot_intent": "support",
    "vpbank_source": "mobile_app",
    "confidence_score": 90,
    "sender_id": 1234567890,
    "recipient_id": 9876543210,
    "page_name": "VPBank Support"
  }'
```

#### Update Workflow
```bash
curl -X PUT "http://localhost:8000/api/v1/facebook-workflow/1" \
  -H "Content-Type: application/json" \
  -d '{
    "answer": "To reset your password, please follow these steps...",
    "state": "answered"
  }'
```

### n8n Workflow Endpoints

#### Sync Workflows
```bash
curl -X POST "http://localhost:8000/api/v1/workflow/sync"
```

#### Get n8n Flows
```bash
curl -X GET "http://localhost:8000/api/v1/n8n-flow"
```

#### Add n8n Flow
```bash
curl -X POST "http://localhost:8000/api/v1/n8n-flow/" \
  -H "Content-Type: application/json" \
  -d '{
    "flow_id": "workflow-id-from-n8n",
    "flow_name": "Customer Support Flow",
    "description": "Handles customer support requests"
  }'
```

### Health Check
```bash
curl http://localhost:8000/api/v1/health
```

### Swagger UI
Access the Swagger UI to test the API:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Database Setup

### PostgreSQL Tables
```sql
-- Facebook Workflow Data
CREATE TABLE facebook_workflow_data (
    id SERIAL PRIMARY KEY,
    user_question TEXT NOT NULL,
    chatbot_intent VARCHAR(100) NOT NULL,
    vpbank_source VARCHAR(100),
    confidence_score INTEGER,
    answer TEXT,
    state VARCHAR(50) DEFAULT 'pending',
    sender_id BIGINT,
    recipient_id BIGINT,
    page_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- n8n Executions
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

-- n8n Flows
CREATE TABLE n8n_flows (
    id SERIAL PRIMARY KEY,
    flow_id VARCHAR(100) UNIQUE NOT NULL,
    flow_name VARCHAR(255),
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    n8n_created_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Scheduler Jobs

The application includes several scheduled jobs:

1. **n8n Workflow Sync** - Runs every 5 minutes to sync active workflows from n8n
2. **n8n Execution Collection** - Runs every minute to collect new workflow executions
3. **Langfuse Processing** - Runs every minute to process executions to Langfuse

## Environment Variables

```
# Database Configuration
DATABASE_URL=postgresql://user:password@host:5432/dbname

# n8n Configuration
N8N_BASE_URL=https://your-n8n-host.com
N8N_API_KEY=your_n8n_api_key
N8N_WORKFLOW_ID=your_workflow_id

# Langfuse Configuration
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_HOST=https://cloud.langfuse.com

# Facebook Webhook
FACEBOOK_WEBHOOK_URL=https://your-webhook-url
```

## Deployment

### Docker Deployment
```bash
# Build and run with Docker
docker build -t multi-agent-platform .
docker run -p 8000:8000 -d multi-agent-platform
```

### Cloud Deployment
The application can be deployed to various cloud platforms:

- **AWS ECS/Fargate**: For containerized deployment
- **AWS Lambda**: For serverless deployment with API Gateway
- **Kubernetes**: For container orchestration

## Monitoring

### Langfuse Observability
- AI model usage tracking
- Token consumption and cost estimation
- Latency monitoring
- Trace visualization

### Application Logs
- Structured JSON format with timestamp, level, message
- Log levels: DEBUG, INFO, WARNING, ERROR

## Project Structure
```
app/
├── configs/          # Configuration settings
├── models/           # Pydantic schemas
├── routes/           # FastAPI routes
├── services/         # Business logic services
│   ├── database_service.py    # Database operations
│   ├── langfuse_service.py    # Langfuse integration
│   ├── n8n_service.py         # n8n API integration
│   ├── scheduler_service.py   # Background jobs
│   └── webhook_service.py     # Webhook integration
├── utils/            # Utility functions
└── main.py           # Application entry point
```

## License

MIT License