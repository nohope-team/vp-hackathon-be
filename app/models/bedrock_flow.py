from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from enum import Enum


class FlowNodeType(str, Enum):
    INPUT = "Input"
    OUTPUT = "Output"
    PROMPT = "Prompt"
    KNOWLEDGE_BASE = "KnowledgeBase"
    LAMBDA = "LambdaFunction"
    CONDITION = "Condition"
    AGENT = "Agent"


class FlowConnection(BaseModel):
    name: str
    source: str
    target: str
    configuration: Optional[Dict[str, Any]] = None


class FlowNode(BaseModel):
    name: str
    type: FlowNodeType
    configuration: Dict[str, Any] = Field(default_factory=dict)


class BedrockFlowDefinition(BaseModel):
    name: str
    description: Optional[str] = None
    nodes: List[FlowNode]
    connections: List[FlowConnection]


class FlowExecutionRequest(BaseModel):
    flow_name: str
    flow_id: Optional[str] = None
    inputs: Dict[str, Any]
    session_id: str


class FlowExecutionResponse(BaseModel):
    flow_id: str
    execution_id: str
    outputs: Dict[str, Any]
    status: str
    execution_time: float