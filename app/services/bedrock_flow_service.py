import json
import uuid
from typing import Dict, Any, List
from datetime import datetime
from app.services.aws_client import aws_client
from app.models.bedrock_flow import BedrockFlowDefinition, FlowExecutionRequest, FlowExecutionResponse
from app.utils.logger import app_logger


class BedrockFlowService:
    """Service for managing Bedrock Flows and multi-agent execution"""
    
    def __init__(self):
        self.bedrock_client = aws_client.session.client('bedrock')
        self.bedrock_agent_client = aws_client.session.client('bedrock-agent')
    
    async def create_flow_from_config(self, flow_config: Dict[str, Any]) -> str:
        """Create Bedrock Flow from JSON configuration"""
        try:
            flow_def = BedrockFlowDefinition(**flow_config)
            
            # Create flow in Bedrock
            response = self.bedrock_agent_client.create_flow(
                name=flow_def.name,
                description=flow_def.description or "",
                executionRoleArn=self._get_execution_role_arn(),
                definition={
                    "nodes": [self._convert_node_to_bedrock_format(node) for node in flow_def.definition.nodes],
                    "connections": [self._convert_connection_to_bedrock_format(conn) for conn in flow_def.definition.connections]
                }
            )
            
            flow_id = response['id']
            app_logger.info(f"Created Bedrock Flow: {flow_id}")
            
            return flow_id
            
        except Exception as e:
            app_logger.error(f"Failed to create flow: {e}")
            raise
    
    async def execute_flow(self, request: FlowExecutionRequest) -> FlowExecutionResponse:
        """Execute Bedrock Flow with inputs"""
        start_time = datetime.utcnow()
        
        try:
            # Prepare flow for execution if needed
            if request.flow_id:
                flow_id = request.flow_id
            else:
                flow_id = await self._get_flow_id_by_name(request.flow_name)
            
            # Prepare flow version
            await self._prepare_flow_version(flow_id)
            
            # Execute flow
            response = self.bedrock_agent_client.invoke_flow(
                flowIdentifier=flow_id,
                flowAliasIdentifier="TSTALIASID",
                inputs=[
                    {
                        "content": {
                            "document": request.inputs
                        },
                        "nodeName": "FlowInputNode",
                        "nodeOutputName": "document"
                    }
                ]
            )
            
            # Process streaming response
            outputs = await self._process_flow_response(response)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return FlowExecutionResponse(
                flow_id=flow_id,
                execution_id=str(uuid.uuid4()),
                outputs=outputs,
                status="COMPLETED",
                execution_time=execution_time
            )
            
        except Exception as e:
            app_logger.error(f"Flow execution failed: {e}")
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return FlowExecutionResponse(
                flow_id=request.flow_id or "unknown",
                execution_id=str(uuid.uuid4()),
                outputs={"error": str(e)},
                status="FAILED",
                execution_time=execution_time
            )
    
    async def create_multi_agent_flow(self, agents_config: List[Dict[str, Any]]) -> str:
        """Create multi-agent flow from agent configurations"""
        nodes = []
        connections = []
        
        # Input node
        nodes.append({
            "name": "InputNode",
            "type": "Input",
            "configuration": {
                "input": {
                    "expression": "$.data"
                }
            }
        })
        
        # Create agent nodes
        for i, agent_config in enumerate(agents_config):
            agent_node = {
                "name": f"Agent_{i+1}_{agent_config['name']}",
                "type": "Agent",
                "configuration": {
                    "agentAliasArn": agent_config.get("agent_arn", ""),
                    "input": {
                        "text": agent_config.get("prompt_template", "$.data")
                    }
                }
            }
            nodes.append(agent_node)
            
            # Connect input to agent
            connections.append({
                "name": f"InputToAgent_{i+1}",
                "source": "InputNode",
                "target": agent_node["name"],
                "configuration": {}
            })
        
        # Aggregator node (Prompt node to combine results)
        aggregator_node = {
            "name": "AggregatorNode",
            "type": "Prompt",
            "configuration": {
                "promptTemplate": {
                    "text": "Combine the following agent responses:\n{% for result in agent_results %}Agent {{ loop.index }}: {{ result }}\n{% endfor %}\nProvide a unified response:"
                }
            }
        }
        nodes.append(aggregator_node)
        
        # Connect all agents to aggregator
        for i, agent_config in enumerate(agents_config):
            connections.append({
                "name": f"Agent_{i+1}_ToAggregator",
                "source": f"Agent_{i+1}_{agent_config['name']}",
                "target": "AggregatorNode",
                "configuration": {}
            })
        
        # Output node
        nodes.append({
            "name": "OutputNode",
            "type": "Output",
            "configuration": {
                "output": {
                    "expression": "$.data"
                }
            }
        })
        
        # Connect aggregator to output
        connections.append({
            "name": "AggregatorToOutput",
            "source": "AggregatorNode",
            "target": "OutputNode",
            "configuration": {}
        })
        
        # Create flow
        flow_config = {
            "name": f"MultiAgent_Flow_{int(datetime.utcnow().timestamp())}",
            "description": "Auto-generated multi-agent flow",
            "nodes": nodes,
            "connections": connections
        }
        
        return await self.create_flow_from_config(flow_config)
    
    def _convert_node_to_bedrock_format(self, node) -> Dict[str, Any]:
        """Convert internal node format to Bedrock format"""
        return {
            "name": node.name,
            "type": node.type.value,
            "configuration": node.configuration,
            "inputs": node.inputs or [],
            "outputs": node.outputs or []
        }
    
    def _convert_connection_to_bedrock_format(self, connection) -> Dict[str, Any]:
        """Convert internal connection format to Bedrock format"""
        return {
            "name": connection.name,
            "source": connection.source,
            "target": connection.target,
            "type": connection.type.value,
            "configuration": connection.configuration or {}
        }
    
    async def _get_flow_id_by_name(self, flow_name: str) -> str:
        """Get flow ID by name"""
        try:
            response = self.bedrock_agent_client.list_flows()
            for flow in response.get('flowSummaries', []):
                if flow['name'] == flow_name:
                    return flow['id']
            raise ValueError(f"Flow not found: {flow_name}")
        except Exception as e:
            app_logger.error(f"Failed to get flow ID: {e}")
            raise
    
    async def _prepare_flow_version(self, flow_id: str):
        """Prepare flow version for execution"""
        try:
            # Create version if not exists
            self.bedrock_agent_client.create_flow_version(
                flowIdentifier=flow_id,
                description="Auto-created version"
            )
        except Exception as e:
            # Version might already exist
            app_logger.debug(f"Flow version creation: {e}")
    
    async def _process_flow_response(self, response) -> Dict[str, Any]:
        """Process streaming flow response"""
        outputs = {}
        
        try:
            for event in response['responseStream']:
                if 'flowOutputEvent' in event:
                    output_event = event['flowOutputEvent']
                    outputs.update(output_event.get('content', {}))
                elif 'flowCompletionEvent' in event:
                    completion_event = event['flowCompletionEvent']
                    outputs['completion_reason'] = completion_event.get('completionReason', 'SUCCESS')
        except Exception as e:
            app_logger.error(f"Error processing flow response: {e}")
            outputs = {"error": "Failed to process flow response"}
        
        return outputs
    
    def _get_execution_role_arn(self) -> str:
        """Get execution role ARN for Bedrock Flow"""
        # This should be configured in settings
        return f"arn:aws:iam::{self._get_account_id()}:role/BedrockFlowExecutionRole"
    
    def _get_account_id(self) -> str:
        """Get AWS account ID"""
        try:
            sts_client = aws_client.session.client('sts')
            return sts_client.get_caller_identity()['Account']
        except:
            return "123456789012"  # fallback


bedrock_flow_service = BedrockFlowService()