import json
import asyncio
from typing import Dict, Any, List, AsyncGenerator
from datetime import datetime
from app.services.aws_client import aws_client
from app.models.flow_chat import FlowChatRequest, FlowChatMessage, FlowChatStreamChunk
from app.utils.logger import app_logger


class FlowChatService:
    """Service for multi-turn conversations with Bedrock Flow"""
    
    def __init__(self):
        self.bedrock_agent_runtime_client = aws_client.bedrock_agent_runtime
        self.dynamodb_client = aws_client.dynamodb
        self.conversation_table = "flow-conversations"
    
    async def chat_with_flow_stream(self, request: FlowChatRequest) -> AsyncGenerator[FlowChatStreamChunk, None]:
        """Stream chat with Bedrock Flow"""
        try:
            # Load conversation history
            conversation_history = await self._load_conversation_history(request.session_id)
            
            # Add current message to history
            user_message = FlowChatMessage(role="user", content=request.message)
            conversation_history.append(user_message)
            
            # Prepare flow inputs with conversation context
            flow_inputs = self._prepare_flow_inputs(request, conversation_history)
            
            yield FlowChatStreamChunk(
                type="metadata",
                content="Starting flow execution...",
                metadata={"flow_id": request.flow_id, "session_id": request.session_id}
            )
            
            # Execute flow with streaming
            async for chunk in self._execute_flow_stream(request.flow_id, flow_inputs):
                yield chunk
            
            # Save conversation history
            assistant_response = await self._get_final_response(request.session_id)
            assistant_message = FlowChatMessage(role="assistant", content=assistant_response)
            conversation_history.append(assistant_message)
            
            await self._save_conversation_history(request.session_id, conversation_history)
            
            yield FlowChatStreamChunk(type="done", content="Flow execution completed")
            
        except Exception as e:
            app_logger.error(f"Flow chat stream error: {e}")
            yield FlowChatStreamChunk(
                type="error",
                content=f"Error: {str(e)}",
                metadata={"error_type": type(e).__name__}
            )
    
    async def _execute_flow_stream(self, flow_id: str, inputs: Dict[str, Any]) -> AsyncGenerator[FlowChatStreamChunk, None]:
        """Execute Bedrock Flow with streaming response"""
        try:
            # Convert inputs to string format for Flow Input Node
            input_text = self._format_inputs_as_text(inputs)
            
            response = self.bedrock_agent_runtime_client.invoke_flow(
                flowIdentifier=flow_id,
                flowAliasIdentifier="TSTALIASID",
                inputs=[
                    {
                        "content": {"document": input_text},
                        "nodeName": "FlowInputNode",
                        "nodeOutputName": "document"
                    }
                ]
            )
            
            accumulated_content = ""
            
            for event in response['responseStream']:
                if 'flowOutputEvent' in event:
                    output_event = event['flowOutputEvent']
                    content = output_event.get('content', {})
                    
                    if 'document' in content:
                        text_content = str(content['document'])
                        accumulated_content += text_content
                        
                        yield FlowChatStreamChunk(
                            type="text",
                            content=text_content,
                            metadata={"node_name": output_event.get('nodeName', '')}
                        )
                
                elif 'flowTraceEvent' in event:
                    trace_event = event['flowTraceEvent']
                    yield FlowChatStreamChunk(
                        type="metadata",
                        content="",
                        metadata={
                            "trace": trace_event.get('trace', {}),
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                
                elif 'flowCompletionEvent' in event:
                    completion_event = event['flowCompletionEvent']
                    yield FlowChatStreamChunk(
                        type="metadata",
                        content="Flow completed",
                        metadata={
                            "completion_reason": completion_event.get('completionReason', 'SUCCESS')
                        }
                    )
                    break
            
            # Store final response for conversation history
            await self._store_temp_response(inputs.get('session_id', ''), accumulated_content)
            
        except Exception as e:
            app_logger.error(f"Flow execution stream error: {e}")
            yield FlowChatStreamChunk(
                type="error",
                content=f"Flow execution failed: {str(e)}"
            )
    
    def _prepare_flow_inputs(self, request: FlowChatRequest, conversation_history: List[FlowChatMessage]) -> Dict[str, Any]:
        """Prepare inputs for flow execution with conversation context"""
        # Format conversation history
        formatted_history = []
        for msg in conversation_history[-10:]:  # Keep last 10 messages
            formatted_history.append({
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            })
        
        # Default flow inputs if not provided
        default_inputs = {
            "context": "general",
            "language": "english",
            "response_style": "conversational",
            "max_history_turns": 10
        }
        
        # Merge with user-provided inputs (user inputs override defaults)
        user_inputs = request.flow_inputs or {}
        merged_inputs = {**default_inputs, **user_inputs}
        
        flow_inputs = {
            "current_message": request.message,
            "conversation_history": formatted_history,
            "session_id": request.session_id,
            "timestamp": datetime.utcnow().isoformat(),
            **merged_inputs
        }
        
        return flow_inputs
    
    async def _load_conversation_history(self, session_id: str) -> List[FlowChatMessage]:
        """Load conversation history from DynamoDB"""
        try:
            response = self.dynamodb_client.get_item(
                TableName=self.conversation_table,
                Key={'session_id': {'S': session_id}}
            )
            
            if 'Item' in response:
                history_data = json.loads(response['Item']['conversation_history']['S'])
                return [FlowChatMessage(**msg) for msg in history_data]
            
            return []
            
        except Exception as e:
            app_logger.error(f"Failed to load conversation history: {e}")
            return []
    
    async def _save_conversation_history(self, session_id: str, conversation_history: List[FlowChatMessage]):
        """Save conversation history to DynamoDB"""
        try:
            history_data = [msg.model_dump(mode='json') for msg in conversation_history]
            
            self.dynamodb_client.put_item(
                TableName=self.conversation_table,
                Item={
                    'session_id': {'S': session_id},
                    'conversation_history': {'S': json.dumps(history_data, default=str)},
                    'updated_at': {'S': datetime.utcnow().isoformat()}
                }
            )
            
        except Exception as e:
            app_logger.error(f"Failed to save conversation history: {e}")
    
    async def _store_temp_response(self, session_id: str, response: str):
        """Store temporary response for conversation history"""
        # Simple in-memory storage for demo
        if not hasattr(self, '_temp_responses'):
            self._temp_responses = {}
        self._temp_responses[session_id] = response
    
    async def _get_final_response(self, session_id: str) -> str:
        """Get final response from temporary storage"""
        if hasattr(self, '_temp_responses'):
            return self._temp_responses.get(session_id, "No response generated")
        return "No response generated"


    def _format_inputs_as_text(self, inputs: Dict[str, Any]) -> str:
        """Format complex inputs as text for Flow Input Node"""
        # Extract key information and format as readable text
        current_message = inputs.get('current_message', '')
        context = inputs.get('context', 'general')
        language = inputs.get('language', 'english')
        
        # Format conversation history
        history_text = ""
        conversation_history = inputs.get('conversation_history', [])
        if conversation_history:
            history_text = "\nConversation History:\n"
            for msg in conversation_history[-3:]:  # Last 3 messages
                history_text += f"{msg['role']}: {msg['content']}\n"
        
        # Create formatted input text
        input_text = f"""Current Message: {current_message}
Context: {context}
Language: {language}{history_text}
Session ID: {inputs.get('session_id', '')}"""
        
        return input_text


flow_chat_service = FlowChatService()