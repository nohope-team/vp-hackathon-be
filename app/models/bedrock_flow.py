from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from enum import Enum

from pydantic_core.core_schema import DefinitionsSchema


class FlowNodeType(str, Enum):
    INPUT = "Input"
    OUTPUT = "Output"
    PROMPT = "Prompt"
    KNOWLEDGE_BASE = "KnowledgeBase"
    LAMBDA = "LambdaFunction"
    CONDITION = "Condition"
    AGENT = "Agent"
class FlowConnectionType(str, Enum):
    CONDITIONAL = "Conditional"
    DATA = "Data"
    SUCCESS = "Success"
    FAILURE = "Failure"

class FlowConnection(BaseModel):
    name: str
    source: str
    target: str
    type: FlowConnectionType
    configuration: Optional[Dict[str, Any]] = None


class FlowNode(BaseModel):
    name: str
    type: FlowNodeType
    configuration: Dict[str, Any] = Field(default_factory=dict)
    inputs: Optional[List[Dict[str, Any]]] = None
    outputs: Optional[List[Dict[str, Any]]] = None

class Definition(BaseModel):
    connections: Optional[List[FlowConnection]]
    nodes: Optional[List[FlowNode]]


class BedrockFlowDefinition(BaseModel):
    name: str
    description: Optional[str] = None
    definition: Definition


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