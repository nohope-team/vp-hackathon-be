from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Any, List
from app.models.bedrock_flow import FlowExecutionRequest, FlowExecutionResponse
from app.models.flow_chat import FlowChatRequest
from app.services.bedrock_flow_service import bedrock_flow_service
from app.services.flow_chat_service import flow_chat_service
from app.utils.logger import app_logger
import json

router = APIRouter(prefix="/api/v1/flow", tags=["bedrock-flow"])


@router.post("/create", response_model=Dict[str, str])
async def create_flow(flow_config: Dict[str, Any]):
    """Create Bedrock Flow from JSON configuration"""
    try:
        flow_id = await bedrock_flow_service.create_flow_from_config(flow_config)
        return {"flow_id": flow_id, "status": "created"}
    except Exception as e:
        app_logger.error(f"Flow creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute", response_model=FlowExecutionResponse)
async def execute_flow(request: FlowExecutionRequest):
    """Execute Bedrock Flow with inputs"""
    try:
        result = await bedrock_flow_service.execute_flow(request)
        return result
    except Exception as e:
        app_logger.error(f"Flow execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create-multi-agent", response_model=Dict[str, str])
async def create_multi_agent_flow(agents_config: List[Dict[str, Any]]):
    """Create multi-agent flow from agent configurations
    
    Example payload:
    [
        {
            "name": "AnalysisAgent",
            "agent_arn": "arn:aws:bedrock:us-east-1:123456789012:agent/AGENT1",
            "prompt_template": "Analyze this data: $.input"
        },
        {
            "name": "RecommendationAgent", 
            "agent_arn": "arn:aws:bedrock:us-east-1:123456789012:agent/AGENT2",
            "prompt_template": "Provide recommendations for: $.input"
        }
    ]
    """
    try:
        flow_id = await bedrock_flow_service.create_multi_agent_flow(agents_config)
        return {"flow_id": flow_id, "status": "multi_agent_flow_created"}
    except Exception as e:
        app_logger.error(f"Multi-agent flow creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-stream")
async def test_flow_stream(request: FlowChatRequest):
    """Test Bedrock Flow with streaming response and multi-turn conversation"""
    try:
        async def generate_stream():
            async for chunk in flow_chat_service.chat_with_flow_stream(request):
                yield f"data: {json.dumps(chunk.model_dump())}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except Exception as e:
        app_logger.error(f"Flow test stream failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))