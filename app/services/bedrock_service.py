import json
import uuid
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError
from app.services.aws_client import aws_client
from app.models.schemas import BedrockAgentRequest
from app.configs.settings import settings
from app.utils.logger import app_logger


class BedrockService:
    """Service for interacting with Amazon Bedrock Agents"""
    
    def __init__(self):
        self.client = aws_client.bedrock_agent_runtime
    
    async def invoke_agent(self, request: BedrockAgentRequest) -> Dict[str, Any]:
        """Invoke Bedrock Agent and return response"""
        try:
            app_logger.info(f"Invoking Bedrock Agent {request.agent_id} for session {request.session_id}")
            
            # Mock response if agent_id is not configured
            if not settings.bedrock_agent_id:
                return self._mock_agent_response(request)
            
            response = self.client.invoke_agent(
                agentId=request.agent_id,
                agentAliasId=request.agent_alias_id,
                sessionId=request.session_id,
                inputText=request.input_text,
                sessionAttributes=request.session_attributes or {},
                promptSessionAttributes=request.prompt_session_attributes or {}
            )
            
            # Process streaming response
            result = self._process_agent_response(response)
            
            app_logger.info(f"Bedrock Agent response received for session {request.session_id}")
            return result
            
        except ClientError as e:
            app_logger.error(f"Bedrock Agent invocation failed: {e}")
            raise
        except Exception as e:
            app_logger.error(f"Unexpected error in Bedrock Agent invocation: {e}")
            raise
    
    def _process_agent_response(self, response) -> Dict[str, Any]:
        """Process streaming response from Bedrock Agent"""
        completion = ""
        citations = []
        trace = []
        
        try:
            for event in response['completion']:
                if 'chunk' in event:
                    chunk = event['chunk']
                    if 'bytes' in chunk:
                        completion += chunk['bytes'].decode('utf-8')
                elif 'trace' in event:
                    trace.append(event['trace'])
                elif 'citation' in event:
                    citations.append(event['citation'])
        except Exception as e:
            app_logger.error(f"Error processing agent response: {e}")
            completion = "Error processing agent response"
        
        return {
            "completion": completion,
            "citations": citations,
            "trace": trace,
            "session_id": response.get('sessionId', '')
        }
    
    def _mock_agent_response(self, request: BedrockAgentRequest) -> Dict[str, Any]:
        """Mock response for development/testing"""
        app_logger.info(f"Using mock response for agent {request.agent_id}")
        
        mock_responses = [
            f"SubAgent-1 processed: {request.input_text[:50]}... Analysis complete.",
            f"SubAgent-2 analyzed: {request.input_text[:50]}... Recommendations generated.",
            f"SubAgent-3 reviewed: {request.input_text[:50]}... Quality check passed."
        ]
        
        return {
            "completion": mock_responses[hash(request.agent_id) % len(mock_responses)],
            "citations": [],
            "trace": [{"step": "mock_processing", "details": "Mock agent execution"}],
            "session_id": request.session_id
        }


bedrock_service = BedrockService()