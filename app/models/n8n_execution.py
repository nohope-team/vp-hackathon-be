from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class N8nExecution(BaseModel):
    id: int
    workflow_id: str
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    execution_data: Optional[Dict[str, Any]] = None
    processed: bool = False
    langfuse_trace_id: Optional[str] = None