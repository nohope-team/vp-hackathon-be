from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime


class FlowChatMessage(BaseModel):
    role: str = Field(..., description="Message role: user, assistant, system")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class FlowChatRequest(BaseModel):
    flow_id: str = Field(..., description="Bedrock Flow ID")
    message: str = Field(..., description="User message")
    session_id: str = Field(..., description="Conversation session ID")
    conversation_history: Optional[List[FlowChatMessage]] = Field(default_factory=list)
    flow_inputs: Optional[Dict[str, Any]] = Field(default_factory=dict)


class FlowChatStreamChunk(BaseModel):
    type: str = Field(..., description="Chunk type: text, metadata, error, done")
    content: str = Field(default="", description="Chunk content")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)