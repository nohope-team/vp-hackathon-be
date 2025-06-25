import boto3
from botocore.exceptions import ClientError
from app.configs.settings import settings
from app.utils.logger import app_logger


class AWSClientManager:
    """Centralized AWS client management"""
    
    def __init__(self):
        self.session = boto3.Session(
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region
        )
    
    @property
    def bedrock_agent_runtime(self):
        return self.session.client('bedrock-agent-runtime')
    
    @property
    def bedrock_agent(self):
        return self.session.client('bedrock-agent')
    
    @property
    def stepfunctions(self):
        return self.session.client('stepfunctions')
    
    @property
    def dynamodb(self):
        if settings.dynamodb_endpoint_url:
            return self.session.client('dynamodb', endpoint_url=settings.dynamodb_endpoint_url)
        return self.session.client('dynamodb')
    
    @property
    def s3(self):
        return self.session.client('s3')
    
    @property
    def sqs(self):
        return self.session.client('sqs')
    
    @property
    def sns(self):
        return self.session.client('sns')
    
    @property
    def lambda_client(self):
        return self.session.client('lambda')


# Global AWS client instance
aws_client = AWSClientManager()