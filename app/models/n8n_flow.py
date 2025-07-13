from pydantic import BaseModel
from typing import Optional

class N8nFlow(BaseModel):
    id: Optional[int] = None
    flow_id: str
    flow_name: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True