import json
import uuid
import asyncio
from typing import Dict, Any, List
from datetime import datetime
from app.services.aws_client import aws_client
from app.services.bedrock_service import bedrock_service
from app.models.schemas import StepFunctionInput, BedrockAgentRequest, AgentExecution, AgentStatus
from app.configs.settings import settings
from app.utils.logger import app_logger


class OrchestratorService:
    """Service for orchestrating multi-agent workflows"""
    
    def __init__(self):
        self.stepfunctions_client = aws_client.stepfunctions
        self.dynamodb_client = aws_client.dynamodb
        self.s3_client = aws_client.s3
    
    async def execute_multi_agent_workflow(self, user_message: str, session_id: str, user_id: str = None) -> Dict[str, Any]:
        """Execute multi-agent workflow orchestration"""
        start_time = datetime.utcnow()
        
        try:
            app_logger.info(f"Starting multi-agent workflow for session {session_id}")
            
            # Step 1: Start Step Functions execution (SuperAgent orchestrator)
            execution_arn = await self._start_step_function(user_message, session_id, user_id)
            
            # Step 2: Execute SubAgents in parallel
            agent_results = await self._execute_sub_agents(user_message, session_id)
            
            # Step 3: Aggregate results
            final_response = await self._aggregate_agent_responses(agent_results, session_id)
            
            # Step 4: Save state to DynamoDB
            await self._save_execution_state(session_id, agent_results, final_response)
            
            # Step 5: Log to S3
            await self._log_to_s3(session_id, {
                "user_message": user_message,
                "agent_results": agent_results,
                "final_response": final_response,
                "execution_time": (datetime.utcnow() - start_time).total_seconds()
            })
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            app_logger.info(f"Multi-agent workflow completed for session {session_id} in {execution_time:.2f}s")
            
            return {
                "response": final_response,
                "session_id": session_id,
                "agents_used": [agent["agent_name"] for agent in agent_results],
                "execution_time": execution_time,
                "status": AgentStatus.COMPLETED,
                "execution_arn": execution_arn
            }
            
        except Exception as e:
            app_logger.error(f"Multi-agent workflow failed for session {session_id}: {e}")
            await self._save_error_state(session_id, str(e))
            raise
    
    async def _start_step_function(self, user_message: str, session_id: str, user_id: str = None) -> str:
        """Start Step Functions execution for SuperAgent orchestration"""
        if not settings.step_function_arn:
            app_logger.info("Step Function ARN not configured, skipping Step Functions execution")
            return f"mock-execution-{uuid.uuid4()}"
        
        try:
            input_data = StepFunctionInput(
                session_id=session_id,
                user_message=user_message,
                user_id=user_id,
                metadata={"timestamp": datetime.utcnow().isoformat()}
            )
            
            response = self.stepfunctions_client.start_execution(
                stateMachineArn=settings.step_function_arn,
                name=f"multi-agent-{session_id}-{int(datetime.utcnow().timestamp())}",
                input=input_data.model_dump_json()
            )
            
            app_logger.info(f"Step Function execution started: {response['executionArn']}")
            return response['executionArn']
            
        except Exception as e:
            app_logger.error(f"Failed to start Step Function: {e}")
            return f"error-execution-{uuid.uuid4()}"
    
    async def _execute_sub_agents(self, user_message: str, session_id: str) -> List[Dict[str, Any]]:
        """Execute multiple SubAgents in parallel"""
        # Define SubAgents (in production, this would come from configuration)
        sub_agents = [
            {"agent_id": "sub-agent-1", "agent_name": "AnalysisAgent", "specialization": "data_analysis"},
            {"agent_id": "sub-agent-2", "agent_name": "RecommendationAgent", "specialization": "recommendations"},
            {"agent_id": "sub-agent-3", "agent_name": "QualityAgent", "specialization": "quality_check"}
        ]
        
        # Execute agents in parallel
        tasks = []
        for agent in sub_agents:
            task = self._execute_single_agent(agent, user_message, session_id)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle exceptions
        agent_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                app_logger.error(f"Agent {sub_agents[i]['agent_name']} failed: {result}")
                agent_results.append({
                    "agent_id": sub_agents[i]["agent_id"],
                    "agent_name": sub_agents[i]["agent_name"],
                    "status": AgentStatus.FAILED,
                    "error": str(result),
                    "response": None
                })
            else:
                agent_results.append(result)
        
        return agent_results
    
    async def _execute_single_agent(self, agent_config: Dict[str, Any], user_message: str, session_id: str) -> Dict[str, Any]:
        """Execute a single SubAgent"""
        start_time = datetime.utcnow()
        
        try:
            # Create specialized prompt based on agent type
            specialized_prompt = self._create_specialized_prompt(agent_config["specialization"], user_message)
            
            # Create Bedrock Agent request
            bedrock_request = BedrockAgentRequest(
                agent_id=settings.bedrock_agent_id or agent_config["agent_id"],
                agent_alias_id=settings.bedrock_agent_alias_id,
                session_id=f"{session_id}-{agent_config['agent_id']}",
                input_text=specialized_prompt
            )
            
            # Invoke Bedrock Agent
            response = await bedrock_service.invoke_agent(bedrock_request)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                "agent_id": agent_config["agent_id"],
                "agent_name": agent_config["agent_name"],
                "status": AgentStatus.COMPLETED,
                "response": response["completion"],
                "execution_time": execution_time,
                "citations": response.get("citations", []),
                "trace": response.get("trace", [])
            }
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            app_logger.error(f"Agent {agent_config['agent_name']} execution failed: {e}")
            
            return {
                "agent_id": agent_config["agent_id"],
                "agent_name": agent_config["agent_name"],
                "status": AgentStatus.FAILED,
                "error": str(e),
                "execution_time": execution_time,
                "response": None
            }
    
    def _create_specialized_prompt(self, specialization: str, user_message: str) -> str:
        """Create specialized prompts for different agent types"""
        prompts = {
            "data_analysis": f"Analyze the following request from a data perspective: {user_message}",
            "recommendations": f"Provide recommendations based on: {user_message}",
            "quality_check": f"Review and validate the quality of this request: {user_message}"
        }
        return prompts.get(specialization, user_message)
    
    async def _aggregate_agent_responses(self, agent_results: List[Dict[str, Any]], session_id: str) -> str:
        """Aggregate responses from multiple agents"""
        successful_responses = [
            result["response"] for result in agent_results 
            if result["status"] == AgentStatus.COMPLETED and result["response"]
        ]
        
        if not successful_responses:
            return "No agents were able to process the request successfully."
        
        # Simple aggregation - in production, this could be more sophisticated
        aggregated_response = f"Multi-Agent Analysis Results:\n\n"
        for i, response in enumerate(successful_responses, 1):
            aggregated_response += f"Agent {i} Response:\n{response}\n\n"
        
        aggregated_response += f"Summary: Processed by {len(successful_responses)} agents successfully."
        
        return aggregated_response
    
    async def _save_execution_state(self, session_id: str, agent_results: List[Dict[str, Any]], final_response: str):
        """Save execution state to DynamoDB"""
        try:
            item = {
                'session_id': {'S': session_id},
                'timestamp': {'S': datetime.utcnow().isoformat()},
                'agent_results': {'S': json.dumps(agent_results)},
                'final_response': {'S': final_response},
                'status': {'S': 'completed'}
            }
            
            self.dynamodb_client.put_item(
                TableName=settings.dynamodb_table_name,
                Item=item
            )
            
            app_logger.info(f"Execution state saved to DynamoDB for session {session_id}")
            
        except Exception as e:
            app_logger.error(f"Failed to save execution state: {e}")
    
    async def _save_error_state(self, session_id: str, error_message: str):
        """Save error state to DynamoDB"""
        try:
            item = {
                'session_id': {'S': session_id},
                'timestamp': {'S': datetime.utcnow().isoformat()},
                'error_message': {'S': error_message},
                'status': {'S': 'failed'}
            }
            
            self.dynamodb_client.put_item(
                TableName=settings.dynamodb_table_name,
                Item=item
            )
            
        except Exception as e:
            app_logger.error(f"Failed to save error state: {e}")
    
    async def _log_to_s3(self, session_id: str, log_data: Dict[str, Any]):
        """Log execution details to S3"""
        try:
            log_key = f"{settings.s3_log_prefix}{datetime.utcnow().strftime('%Y/%m/%d')}/{session_id}.json"
            
            self.s3_client.put_object(
                Bucket=settings.s3_bucket_name,
                Key=log_key,
                Body=json.dumps(log_data, default=str),
                ContentType='application/json'
            )
            
            app_logger.info(f"Execution log saved to S3: s3://{settings.s3_bucket_name}/{log_key}")
            
        except Exception as e:
            app_logger.error(f"Failed to log to S3: {e}")


orchestrator_service = OrchestratorService()