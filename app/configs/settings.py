from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    # AWS Configuration
    aws_region: str = "us-east-1"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    
    # Bedrock Configuration
    bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    bedrock_agent_id: Optional[str] = None
    bedrock_agent_alias_id: str = "TSTALIASID"
    
    # Step Functions
    step_function_arn: Optional[str] = None
    
    # SQS/SNS
    sqs_queue_url: Optional[str] = None
    sns_topic_arn: Optional[str] = None
    
    # DynamoDB
    dynamodb_table_name: str = "multi-agent-state"
    dynamodb_endpoint_url: Optional[str] = None
    
    # S3
    s3_bucket_name: str = "multi-agent-logs"
    s3_log_prefix: str = "logs/"
    
    # Application
    app_name: str = "MultiAgentPlatform"
    app_version: str = "1.0.0"
    log_level: str = "INFO"
    environment: str = "development"

    database_url: Optional[str] = None
    # VPC Configuration
    vpc_id: Optional[str] = None
    subnet_ids: Optional[str] = None
    security_group_id: Optional[str] = None

    facebook_webhook_url: Optional[str] = "https://dungcao1.app.n8n.cloud/webhook/ff25c7f4-0279-4f76-a12a-caecbf188f52"
    
    # n8n Configuration
    n8n_base_url: str = "http://localhost:5678"
    n8n_api_key: Optional[str] = None
    n8n_workflow_id: Optional[str] = None
    
    # Langfuse Configuration
    langfuse_secret_key: str= "sk-lf-40484669-8a8e-4fdf-8f70-296c2deef06a"
    langfuse_public_key: str= "pk-lf-e2285dc1-130f-46a0-a4ec-309e7cf3be98"
    langfuse_host: str = "https://cloud.langfuse.com"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()