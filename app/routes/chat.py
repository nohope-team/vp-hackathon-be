import uuid
from fastapi import APIRouter, HTTPException, Depends
from app.models.schemas import ChatRequest, ChatResponse, AgentStatus
from app.services.orchestrator_service import orchestrator_service
from app.utils.logger import app_logger

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Main chat endpoint that processes user messages through multi-agent system
    """
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        app_logger.info(f"Processing chat request for session {session_id}")
        
        # Execute multi-agent workflow
        result = await orchestrator_service.execute_multi_agent_workflow(
            user_message=request.message,
            session_id=session_id,
            user_id=request.user_id
        )
        
        # Return structured response
        return ChatResponse(
            response=result["response"],
            session_id=result["session_id"],
            agents_used=result["agents_used"],
            execution_time=result["execution_time"],
            status=result["status"]
        )
        
    except Exception as e:
        app_logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "multi-agent-platform",
        "version": "1.0.0"
    }