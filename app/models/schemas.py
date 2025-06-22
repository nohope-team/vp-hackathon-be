from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message to process")
    session_id: Optional[str] = Field(None, description="Session ID for conversation tracking")
    user_id: Optional[str] = Field(None, description="User ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    response: str = Field(..., description="Aggregated response from agents")
    session_id: str = Field(..., description="Session ID")
    agents_used: List[str] = Field(default_factory=list, description="List of agents that processed the request")
    execution_time: float = Field(..., description="Total execution time in seconds")
    status: AgentStatus = Field(..., description="Overall execution status")


class AgentExecution(BaseModel):
    agent_id: str
    agent_name: str
    status: AgentStatus
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class StepFunctionInput(BaseModel):
    session_id: str
    user_message: str
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BedrockAgentRequest(BaseModel):
    agent_id: str
    agent_alias_id: str
    session_id: str
    input_text: str
    session_attributes: Optional[Dict[str, str]] = None
    prompt_session_attributes: Optional[Dict[str, str]] = None