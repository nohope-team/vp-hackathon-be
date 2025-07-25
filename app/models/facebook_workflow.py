from pydantic import BaseModel
from typing import Optional

class FacebookWorkflowData(BaseModel):
    id: Optional[int] = None
    user_question: str
    chatbot_intent: str
    vpbank_source: Optional[str] = None
    confidence_score: Optional[int] = None
    answer: Optional[str] = None
    state: Optional[str] = "pending"
    sender_id: Optional[int] = None
    recipient_id: Optional[int] = None
    page_name: Optional[str] = None

class FacebookWorkflowUpdate(BaseModel):
    chatbot_intent: Optional[str] = None
    vpbank_source: Optional[str] = None
    confidence_score: Optional[int] = None
    answer: Optional[str] = None
    state: Optional[str] = None
    sender_id: Optional[int] = None
    recipient_id: Optional[int] = None
    page_name: Optional[str] = None