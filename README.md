# Multi-Agent Platform Backend

Hệ thống backend FastAPI cho multi-agent platform sử dụng Amazon Bedrock Architecture.

## Kiến trúc

```
API Gateway → FastAPI → Step Functions (SuperAgent) → Bedrock Agents (SubAgents)
                    ↓
            SQS/SNS → Lambda (Tools/Plugins)
                    ↓
            DynamoDB (State) + S3 (Logs) + CloudWatch/X-Ray (Monitoring)
```

## Tính năng

- ✅ REST API endpoint `/chat` để nhận yêu cầu từ client
- ✅ Tích hợp Step Functions để khởi tạo SuperAgent orchestrator
- ✅ Giao tiếp với Amazon Bedrock để tạo và quản lý SubAgents
- ✅ Hỗ trợ SQS/SNS để tích hợp Lambda functions
- ✅ Lưu trữ state trong DynamoDB và logs trong S3
- ✅ Monitoring với CloudWatch và X-Ray tracing
- ✅ Structured JSON logging
- ✅ Docker containerization
- ✅ Swagger UI/ReDoc documentation

## Cài đặt Local

### Yêu cầu
- Python 3.10+
- Docker & Docker Compose
- AWS CLI configured

### Bước 1: Clone và setup
```bash
git clone <repository>
cd VPHackathon
```

### Bước 2: Cấu hình môi trường
```bash
# Copy và chỉnh sửa file .env
cp .env.example .env
# Cập nhật các giá trị AWS credentials và ARNs
```

### Bước 3: Cài đặt dependencies
```bash
# Tạo virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Cài đặt packages
pip install -r requirements.txt
```

### Bước 4: Chạy ứng dụng

#### Option 1: Chạy trực tiếp
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Option 2: Sử dụng Docker
```bash
# Build và chạy
docker-compose up --build

# Chạy với local DynamoDB
docker-compose --profile local up --build

# Chạy với X-Ray daemon
docker-compose --profile xray up --build
```

## API Usage

### Bedrock Flow Endpoints

#### Create Flow from JSON Config
```bash
curl -X POST "http://localhost:8000/api/v1/flow/create" \
  -H "Content-Type: application/json" \
  -d @examples/flow_config.json
```

#### Create Multi-Agent Flow
```bash
curl -X POST "http://localhost:8000/api/v1/flow/create-multi-agent" \
  -H "Content-Type: application/json" \
  -d @examples/multi_agent_config.json
```

#### Execute Flow
```bash
curl -X POST "http://localhost:8000/api/v1/flow/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "flow_name": "CustomerSupportMultiAgent",
    "inputs": {
      "customer_query": "I need help with my order"
    },
    "session_id": "flow-session-123"
  }'
```

### Chat Endpoint
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Analyze the market trends for Q4 2024",
    "session_id": "test-session-123",
    "user_id": "user-456"
  }'
```

### Response Format
```json
{
  "response": "Multi-Agent Analysis Results:\n\nAgent 1 Response:\nSubAgent-1 processed: Analyze the market trends for Q4 2024... Analysis complete.\n\nAgent 2 Response:\nSubAgent-2 analyzed: Analyze the market trends for Q4 2024... Recommendations generated.\n\nAgent 3 Response:\nSubAgent-3 reviewed: Analyze the market trends for Q4 2024... Quality check passed.\n\nSummary: Processed by 3 agents successfully.",
  "session_id": "test-session-123",
  "agents_used": ["AnalysisAgent", "RecommendationAgent", "QualityAgent"],
  "execution_time": 2.45,
  "status": "completed"
}
```

### Health Check
```bash
curl http://localhost:8000/api/v1/health
```

### Swagger UI
Truy cập giao diện Swagger để test API:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## AWS Services Setup

### 1. DynamoDB Table
```bash
aws dynamodb create-table \
  --table-name multi-agent-state \
  --attribute-definitions AttributeName=session_id,AttributeType=S \
  --key-schema AttributeName=session_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

### 2. S3 Bucket
```bash
aws s3 mb s3://multi-agent-logs
```

### 3. Step Functions State Machine
```json
{
  "Comment": "Multi-Agent Orchestrator",
  "StartAt": "InitializeSuperAgent",
  "States": {
    "InitializeSuperAgent": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "SuperAgentFunction",
        "Payload.$": "$"
      },
      "End": true
    }
  }
}
```

### 4. IAM Role
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeAgent",
        "bedrock:InvokeModel",
        "states:StartExecution",
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "s3:PutObject",
        "sqs:SendMessage",
        "sns:Publish",
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords"
      ],
      "Resource": "*"
    }
  ]
}
```

## Deploy lên AWS

### ECS Deployment
```bash
# Build và push image
docker build -t multi-agent-platform .
docker tag multi-agent-platform:latest <account-id>.dkr.ecr.<region>.amazonaws.com/multi-agent-platform:latest
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/multi-agent-platform:latest

# Deploy ECS service
aws ecs create-service \
  --cluster multi-agent-cluster \
  --service-name multi-agent-service \
  --task-definition multi-agent-task \
  --desired-count 2
```

### EKS Deployment
```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: multi-agent-platform
spec:
  replicas: 3
  selector:
    matchLabels:
      app: multi-agent-platform
  template:
    metadata:
      labels:
        app: multi-agent-platform
    spec:
      containers:
      - name: api
        image: <account-id>.dkr.ecr.<region>.amazonaws.com/multi-agent-platform:latest
        ports:
        - containerPort: 8000
        env:
        - name: AWS_REGION
          value: "us-east-1"
        # Add other environment variables
```

```bash
kubectl apply -f k8s-deployment.yaml
```

## Monitoring

### CloudWatch Logs
- Application logs: `/aws/ecs/multi-agent-platform`
- Structured JSON format với timestamp, level, message

### X-Ray Tracing
- Trace requests qua các AWS services
- Performance monitoring cho từng agent execution

### Metrics
- Request count và latency
- Agent execution success/failure rates
- DynamoDB và S3 operation metrics

## Development

### Cấu trúc thư mục
```
app/
├── configs/          # Configuration settings
├── models/           # Pydantic schemas
├── routes/           # FastAPI routes
├── services/         # Business logic services
├── utils/            # Utility functions
└── main.py          # Application entry point
```

### Testing
```bash
# Chạy tests (khi có)
pytest tests/

# Test với mock data
python -m pytest tests/ -v
```

### Logging
- Sử dụng structured JSON logging
- Log levels: DEBUG, INFO, WARNING, ERROR
- Automatic log rotation và retention

## Troubleshooting

### Common Issues

1. **AWS Credentials**
   ```bash
   aws configure
   # hoặc set environment variables
   ```

2. **DynamoDB Connection**
   ```bash
   # Test connection
   aws dynamodb list-tables
   ```

3. **Bedrock Access**
   ```bash
   # Enable Bedrock models
   aws bedrock list-foundation-models
   ```

4. **Docker Issues**
   ```bash
   # Rebuild without cache
   docker-compose build --no-cache
   ```

## License

MIT License