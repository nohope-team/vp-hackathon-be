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

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()